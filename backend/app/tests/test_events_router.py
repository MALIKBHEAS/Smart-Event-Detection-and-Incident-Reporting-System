from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from app.auth.dependencies import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.camera import Camera
from app.models.event import Event
from app.models.report import Report
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    session = SessionFactory()

    camera = Camera(name="Lobby", rtsp_url="rtsp://lobby", enabled=True)
    session.add(camera)
    session.commit()
    session.refresh(camera)

    report = Report(title="R1", summary="s", severity="high", status="open")
    session.add(report)
    session.commit()
    session.refresh(report)

    now = datetime.utcnow()
    session.add(Event(camera_id=camera.id, report_id=report.id, type="restricted_area", severity="high", timestamp=now, payload={"score": 0.9}))
    session.add(Event(camera_id=camera.id, report_id=None, type="loitering", severity="low", timestamp=now - timedelta(hours=2), payload={}))
    session.add(Event(camera_id=None, report_id=None, type="suspicious_object", severity="medium", timestamp=now - timedelta(days=1), payload={}))
    session.commit()

    def override_get_db():
        yield session

    def override_get_current_user():
        return SimpleNamespace(id=1, username="test", is_active=True, roles=[SimpleNamespace(name="Viewer")])

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        yield TestClient(app), camera, report
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        session.close()


def test_list_events_returns_all(client) -> None:
    test_client, _camera, _report = client
    resp = test_client.get("/events")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_list_events_filter_by_camera(client) -> None:
    test_client, camera, _report = client
    resp = test_client.get("/events", params={"camera_id": camera.id})
    assert resp.json()["total"] == 2


def test_list_events_filter_by_type_and_severity(client) -> None:
    test_client, _camera, _report = client
    resp = test_client.get("/events", params={"event_type": "loitering"})
    assert resp.json()["total"] == 1
    resp = test_client.get("/events", params={"severity": "high"})
    assert resp.json()["total"] == 1


def test_list_events_filter_by_report_id(client) -> None:
    test_client, _camera, report = client
    resp = test_client.get("/events", params={"report_id": report.id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["report_id"] == report.id


def test_list_events_filter_by_linked(client) -> None:
    test_client, _camera, _report = client
    resp = test_client.get("/events", params={"linked_only": True})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["linked"] is True

    resp = test_client.get("/events", params={"linked_only": False})
    assert resp.json()["total"] == 2


def test_list_events_date_range(client) -> None:
    test_client, _camera, _report = client
    since = (datetime.utcnow() - timedelta(hours=6)).isoformat()
    resp = test_client.get("/events", params={"start_time": since})
    # Excludes only the event from 1 day ago; the 'now' and '2 hours ago'
    # events both fall within this 6-hour window.
    assert resp.json()["total"] == 2


def test_get_event_detail_and_404(client) -> None:
    test_client, _camera, _report = client
    listed = test_client.get("/events").json()["items"][0]
    resp = test_client.get(f"/events/{listed['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == listed["id"]

    assert test_client.get("/events/999999").status_code == 404


def test_list_event_types(client) -> None:
    test_client, _camera, _report = client
    resp = test_client.get("/events/types")
    assert resp.status_code == 200
    assert set(resp.json()["types"]) == {"restricted_area", "loitering", "suspicious_object"}


def test_events_require_authentication() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    session = SessionFactory()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            assert test_client.get("/events").status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
