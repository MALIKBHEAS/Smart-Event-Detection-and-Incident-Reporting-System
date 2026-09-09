from __future__ import annotations

import app.db.session as app_db_session
from app.db.base import Base
from app.main import app
from app.providers.worker_manager_provider import MockWorkerManager
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class RouteWorkerManager(MockWorkerManager):
    def __init__(self) -> None:
        super().__init__()
        self.started: list[int] = []
        self.stopped: list[int] = []

    async def start_camera(self, camera_identifier) -> bool:
        self.started.append(int(camera_identifier))
        return await super().start_camera(camera_identifier)

    async def stop_camera(self, camera_identifier) -> bool:
        self.stopped.append(int(camera_identifier))
        return await super().stop_camera(camera_identifier)


def setup_database() -> tuple[object, sessionmaker]:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, SessionFactory


def test_camera_crud_routes(monkeypatch):
    original_engine = app_db_session.engine
    original_session_local = app_db_session.SessionLocal
    engine, SessionFactory = setup_database()
    app_db_session.engine = engine
    app_db_session.SessionLocal = SessionFactory
    dummy_manager = RouteWorkerManager()
    monkeypatch.setattr(
        "app.providers.worker_manager_provider.create_worker_manager",
        lambda settings=None: dummy_manager,
    )

    payload = {
        "name": "Lobby Cam",
        "rtsp_url": "rtsp://127.0.0.1/lobby",
        "location": "Main lobby",
        "enabled": True,
        "detector_config": {"fps": 2.0, "confidence_threshold": 0.4},
        "tracker_config": {"use_byte": False},
    }

    try:
        with TestClient(app) as client:
            register_resp = client.post(
                "/auth/register",
                json={"username": "admin", "email": "admin@example.com", "password": "supersecret123"},
            )
            assert register_resp.status_code == 201
            login_resp = client.post("/auth/login", json={"username": "admin", "password": "supersecret123"})
            assert login_resp.status_code == 200
            client.headers.update({"Authorization": f"Bearer {login_resp.json()['access_token']}"})

            create_resp = client.post("/cameras", json=payload)
            assert create_resp.status_code == 201
            camera = create_resp.json()
            assert camera["name"] == payload["name"]
            assert camera["enabled"] is True
            assert camera["id"] is not None

            list_resp = client.get("/cameras")
            assert list_resp.status_code == 200
            assert isinstance(list_resp.json(), list)
            assert any(item["id"] == camera["id"] for item in list_resp.json())

            detail_resp = client.get(f"/cameras/{camera['id']}")
            assert detail_resp.status_code == 200
            assert detail_resp.json()["name"] == payload["name"]

            update_resp = client.put(
                f"/cameras/{camera['id']}",
                json={"enabled": False, "location": "Lobby foyer"},
            )
            assert update_resp.status_code == 200
            assert update_resp.json()["enabled"] is False
            assert update_resp.json()["location"] == "Lobby foyer"

            delete_resp = client.delete(f"/cameras/{camera['id']}")
            assert delete_resp.status_code == 204
    finally:
        if hasattr(app_db_session, "engine"):
            app_db_session.engine.dispose()
        app_db_session.engine = original_engine
        app_db_session.SessionLocal = original_session_local

    assert dummy_manager.started == [camera["id"]]
    assert dummy_manager.stopped == [camera["id"], camera["id"]]
