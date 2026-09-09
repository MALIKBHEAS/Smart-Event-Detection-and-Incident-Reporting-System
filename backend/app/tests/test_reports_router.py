"""Tests for the reports router (app/routers/reports.py).

Uses an isolated in-memory SQLite DB (via get_db override) rather than the
shared dev.db, consistent with test_auth.py / test_intelligence_analytics.py.
"""
from __future__ import annotations

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

    def override_get_db():
        yield session

    def override_get_current_user():
        return SimpleNamespace(id=1, username="admin", is_active=True, roles=[SimpleNamespace(name="Admin")])

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        session.close()


def test_create_get_update_delete_report(client) -> None:
    test_client, _session = client

    create_resp = test_client.post(
        "/reports",
        json={"title": "Unauthorized access", "summary": "Someone entered restricted area", "severity": "high", "status": "open"},
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["title"] == "Unauthorized access"
    assert body["event_count"] == 0
    report_id = body["id"]

    get_resp = test_client.get(f"/reports/{report_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == report_id

    update_resp = test_client.put(f"/reports/{report_id}", json={"status": "resolved"})
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "resolved"

    delete_resp = test_client.delete(f"/reports/{report_id}")
    assert delete_resp.status_code == 204

    missing_resp = test_client.get(f"/reports/{report_id}")
    assert missing_resp.status_code == 404


def test_create_report_triggers_notification(client) -> None:
    from app.models.notification import Notification

    test_client, session = client
    resp = test_client.post(
        "/reports",
        json={"title": "Notify me", "summary": "s", "severity": "critical", "status": "open"},
    )
    assert resp.status_code == 201
    report_id = resp.json()["id"]

    notifications = session.query(Notification).filter(Notification.related_id == report_id).all()
    assert len(notifications) == 1
    assert notifications[0].type == "new_incident"
    assert "Notify me" in notifications[0].message


def test_status_change_triggers_notification(client) -> None:
    from app.models.notification import Notification

    test_client, session = client
    resp = test_client.post("/reports", json={"title": "Status test", "summary": "s", "severity": "low", "status": "open"})
    report_id = resp.json()["id"]

    update_resp = test_client.put(f"/reports/{report_id}", json={"status": "resolved"})
    assert update_resp.status_code == 200

    notifications = session.query(Notification).filter(Notification.related_id == report_id, Notification.type == "incident_updated").all()
    assert len(notifications) == 1
    assert "resolved" in notifications[0].message


def test_get_update_delete_missing_report_returns_404(client) -> None:
    test_client, _session = client
    assert test_client.get("/reports/999").status_code == 404
    assert test_client.put("/reports/999", json={"status": "resolved"}).status_code == 404
    assert test_client.delete("/reports/999").status_code == 404


def test_list_reports_filtering_search_pagination_sorting(client) -> None:
    test_client, session = client
    camera = Camera(name="Lobby Cam", rtsp_url="rtsp://lobby", enabled=True)
    session.add(camera)
    session.commit()
    session.refresh(camera)

    test_client.post("/reports", json={"title": "Alpha breach", "summary": "s1", "severity": "high", "status": "open", "camera_id": camera.id})
    test_client.post("/reports", json={"title": "Beta loitering", "summary": "s2", "severity": "low", "status": "resolved"})
    test_client.post("/reports", json={"title": "Gamma object", "summary": "s3", "severity": "medium", "status": "open"})

    # filter by status
    resp = test_client.get("/reports", params={"status": "open"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(item["status"] == "open" for item in body["items"])

    # filter by severity
    resp = test_client.get("/reports", params={"severity": "low"})
    assert resp.json()["total"] == 1

    # filter by camera_id
    resp = test_client.get("/reports", params={"camera_id": camera.id})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "Alpha breach"

    # search
    resp = test_client.get("/reports", params={"search": "loitering"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "Beta loitering"

    # pagination
    resp = test_client.get("/reports", params={"page": 1, "page_size": 2})
    assert len(resp.json()["items"]) == 2
    assert resp.json()["total"] == 3

    # sorting
    resp = test_client.get("/reports", params={"sort_by": "title", "sort_dir": "asc"})
    titles = [item["title"] for item in resp.json()["items"]]
    assert titles == sorted(titles)


def test_event_count_reflects_linked_events(client) -> None:
    test_client, session = client

    create_resp = test_client.post("/reports", json={"title": "Cluster", "summary": "s", "severity": "high", "status": "open"})
    report_id = create_resp.json()["id"]
    assert create_resp.json()["event_count"] == 0

    report = session.get(Report, report_id)
    session.add(Event(camera_id=None, report_id=report.id, type="restricted_area", severity="high", timestamp=None, payload={}))
    session.add(Event(camera_id=None, report_id=report.id, type="restricted_area", severity="high", timestamp=None, payload={}))
    session.commit()

    get_resp = test_client.get(f"/reports/{report_id}")
    assert get_resp.json()["event_count"] == 2

    list_resp = test_client.get("/reports")
    assert list_resp.json()["items"][0]["event_count"] == 2


def test_download_pdf_and_csv(client) -> None:
    test_client, _session = client
    create_resp = test_client.post(
        "/reports",
        json={"title": "Downloadable report", "summary": "For export testing", "severity": "critical", "status": "open"},
    )
    report_id = create_resp.json()["id"]

    pdf_resp = test_client.get(f"/reports/{report_id}/download/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content[:4] == b"%PDF"
    assert f'report-{report_id}.pdf' in pdf_resp.headers["content-disposition"]

    csv_resp = test_client.get(f"/reports/{report_id}/download/csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "Downloadable report" in csv_resp.text
    assert f'report-{report_id}.csv' in csv_resp.headers["content-disposition"]


def test_download_missing_report_returns_404(client) -> None:
    test_client, _session = client
    assert test_client.get("/reports/999/download/pdf").status_code == 404
    assert test_client.get("/reports/999/download/csv").status_code == 404


# ---------------------------------------------------------------------------
# Auth enforcement (separate from the fixture above, which stubs a fixed
# Admin user -- these check the real role gate using distinct overrides).
# ---------------------------------------------------------------------------


def test_reports_require_authentication() -> None:
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
            assert test_client.get("/reports").status_code == 401
            assert test_client.post("/reports", json={"title": "x", "summary": "y"}).status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()


def test_viewer_cannot_write_reports() -> None:
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

    def override_get_current_user():
        return SimpleNamespace(id=2, username="viewer", is_active=True, roles=[SimpleNamespace(name="Viewer")])

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        with TestClient(app) as test_client:
            # Viewer can read...
            assert test_client.get("/reports").status_code == 200
            # ...but not write.
            resp = test_client.post("/reports", json={"title": "x", "summary": "y", "severity": "low", "status": "open"})
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        session.close()
