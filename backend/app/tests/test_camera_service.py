from __future__ import annotations

import asyncio
from typing import Dict

from app.db.base import Base
from app.providers.worker_manager_provider import MockWorkerManager
from app.schemas.camera import CameraCreate, CameraUpdate
from app.services.camera_service import CameraService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DummyWorkerManager(MockWorkerManager):
    def __init__(self) -> None:
        super().__init__()
        self.started: Dict[int, int] = {}
        self.stopped: Dict[int, int] = {}
        self.restarted: Dict[int, int] = {}

    async def start_camera(self, camera_identifier) -> bool:
        result = await super().start_camera(camera_identifier)
        self.started[int(camera_identifier)] = self.started.get(int(camera_identifier), 0) + 1
        return result

    async def stop_camera(self, camera_identifier) -> bool:
        result = await super().stop_camera(camera_identifier)
        self.stopped[int(camera_identifier)] = self.stopped.get(int(camera_identifier), 0) + 1
        return result

    async def restart_camera(self, camera_identifier) -> bool:
        self.restarted[int(camera_identifier)] = self.restarted.get(int(camera_identifier), 0) + 1
        return await super().restart_camera(camera_identifier)


def setup_database() -> tuple[object, sessionmaker]:
    engine = create_engine("sqlite:///:memory:", future=True)
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    return engine, SessionFactory


def teardown_database(session) -> None:
    session.close()


def test_camera_service_create_and_start_worker():
    _, SessionFactory = setup_database()
    session = SessionFactory()
    worker_manager = DummyWorkerManager()
    try:
        service = CameraService(session, worker_manager)
        camera_create = CameraCreate(
            name="Entrance Cam",
            rtsp_url="rtsp://127.0.0.1/test",
            location="Front lobby",
            enabled=True,
            detector_config={"fps": 5.0, "confidence_threshold": 0.2},
            tracker_config={"use_byte": False},
        )
        camera = asyncio.run(service.create_camera(camera_create))
        assert camera.id is not None
        assert camera.enabled is True
        assert worker_manager.started.get(camera.id, 0) == 1
    finally:
        teardown_database(session)


def test_camera_service_update_disables_and_stops_worker():
    _, SessionFactory = setup_database()
    session = SessionFactory()
    worker_manager = DummyWorkerManager()
    try:
        service = CameraService(session, worker_manager)
        camera = asyncio.run(
            service.create_camera(
                CameraCreate(
                    name="Back Cam",
                    rtsp_url="rtsp://127.0.0.1/back",
                    location="Back entrance",
                    enabled=True,
                    detector_config={"fps": 1.0},
                    tracker_config={"use_byte": True},
                )
            )
        )
        assert worker_manager.started.get(camera.id, 0) == 1

        updated = asyncio.run(
            service.update_camera(camera.id, CameraUpdate(enabled=False))
        )
        assert updated.enabled is False
        assert worker_manager.stopped.get(camera.id, 0) == 1
    finally:
        teardown_database(session)
