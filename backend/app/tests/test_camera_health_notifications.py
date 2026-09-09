"""Tests for camera/worker connection-state-change notifications (Gap 3)."""
from __future__ import annotations

import app.workers.worker as worker_module
from app.db.base import Base
from app.models.notification import Notification
from app.workers.worker import RTSPDetectionWorker, WorkerConfig
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _make_isolated_db():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    return engine, SessionFactory


def test_set_connected_fires_notification_only_on_transition():
    engine, SessionFactory = _make_isolated_db()
    original_session_local = worker_module.SessionLocal
    worker_module.SessionLocal = SessionFactory

    try:
        config = WorkerConfig(source=0, camera_id=42, camera_name="gap3-cam", fps=1.0)
        worker = RTSPDetectionWorker(config)
        assert worker._connected is False

        # False -> False: no real transition, no notification.
        worker._set_connected(False)
        session = SessionFactory()
        assert session.query(Notification).count() == 0
        session.close()

        # False -> True: real transition, one "camera_online" notification.
        worker._set_connected(True)
        session = SessionFactory()
        notifications = session.query(Notification).all()
        assert len(notifications) == 1
        assert notifications[0].type == "camera_online"
        assert "gap3-cam" in notifications[0].message
        session.close()

        # True -> True again: repeated identical state must NOT spam.
        worker._set_connected(True)
        worker._set_connected(True)
        session = SessionFactory()
        assert session.query(Notification).count() == 1
        session.close()

        # True -> False: real transition, second "camera_offline" notification.
        worker._set_connected(False)
        session = SessionFactory()
        notifications = session.query(Notification).order_by(Notification.id).all()
        assert len(notifications) == 2
        assert notifications[1].type == "camera_offline"
        session.close()
    finally:
        engine.dispose()
        worker_module.SessionLocal = original_session_local
