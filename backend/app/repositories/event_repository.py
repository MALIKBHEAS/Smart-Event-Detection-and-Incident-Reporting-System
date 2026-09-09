"""Repository implementation for persisting fused event domain models."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, cast

from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.event import EventData, EventSeverity
from app.models.event import Event

logger = logging.getLogger(__name__)


class EventRepository:
    """Repository that persists domain EventData into the SQLAlchemy Event model."""

    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    def save(self, event_data: EventData) -> int:
        session = self._session_factory()
        try:
            if event_data.id is not None:
                existing = session.get(Event, event_data.id)
                if existing is not None:
                    existing.camera_id = event_data.camera_id
                    existing.type = event_data.event_type
                    existing.severity = event_data.severity.value
                    existing.timestamp = event_data.timestamp
                    existing.payload = self._serialize_payload(event_data.payload, event_data.screenshot_path)
                    # preserve/report association if provided
                    existing.report_id = event_data.report_id
                    session.add(existing)
                    session.commit()
                    session.refresh(existing)
                    return cast(int, existing.id)

            event_model = Event(
                camera_id=event_data.camera_id,
                type=event_data.event_type,
                severity=event_data.severity.value,
                timestamp=event_data.timestamp,
                payload=self._serialize_payload(event_data.payload, event_data.screenshot_path),
                report_id=event_data.report_id,
            )
            session.add(event_model)
            session.commit()
            session.refresh(event_model)
            return cast(int, event_model.id)
        except Exception:
            logger.exception("Failed to save EventData to repository")
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
            raise
        finally:
            session.close()

    def find_recent_by_camera_and_type(
        self, camera_id: int, event_type: str, within_seconds: int = 60
    ) -> Optional[EventData]:
        session = self._session_factory()
        try:
            cutoff = datetime.utcnow() - timedelta(seconds=within_seconds)
            statement = (
                select(Event)
                .where(Event.camera_id == camera_id)
                .where(Event.type == event_type)
                .where(Event.timestamp >= cutoff)
                .order_by(Event.timestamp.desc())
                .limit(1)
            )
            row = session.execute(statement).scalars().first()
            if row is None:
                return None
            return self._to_event_data(row)
        except Exception:
            logger.exception("Failed to query recent EventData from repository")
            raise
        finally:
            session.close()

    @staticmethod
    def _serialize_payload(payload: Dict[str, Any], screenshot_path: str | None) -> Dict[str, Any]:
        merged = dict(payload)
        if screenshot_path is not None:
            merged["screenshot_path"] = screenshot_path
        return merged

    @staticmethod
    def _to_event_data(event_model: Event) -> EventData:
        return EventData(
            id=cast(int, event_model.id),
            camera_id=cast(int, event_model.camera_id),
            camera_name="",
            event_type=cast(str, event_model.type),
            severity=EventSeverity(cast(str, event_model.severity)),
            score=0.0,
            timestamp=cast(datetime, event_model.timestamp),
            payload=cast(Dict[str, Any], event_model.payload or {}),
        )
