from __future__ import annotations

import datetime
from typing import Optional

from app.domain.event import EventData, EventSeverity
from app.repositories.event_repository import EventRepository
from app.services.event_fusion_service import EventFusionService


class DummyRepository(EventRepository):
    def __init__(self, existing_event: Optional[EventData] = None) -> None:
        self.existing_event = existing_event
        self.saved: list[EventData] = []

    def save(self, event_data: EventData) -> int:
        self.saved.append(event_data)
        return event_data.id or 100

    def find_recent_by_camera_and_type(
        self,
        camera_id: int,
        event_type: str,
        within_seconds: int = 30,
    ) -> EventData | None:
        return self.existing_event


def test_event_data_severity_mapping() -> None:
    assert EventSeverity.from_score(0.85) == EventSeverity.HIGH
    assert EventSeverity.from_score(0.6) == EventSeverity.MEDIUM
    assert EventSeverity.from_score(0.1) == EventSeverity.LOW


def test_event_fusion_service_ingests_new_event() -> None:
    repository = DummyRepository()
    service = EventFusionService(repository=repository)
    event = EventData(
        camera_id=1,
        camera_name="camera-1",
        event_type="person",
        severity=EventSeverity.LOW,
        score=0.4,
        timestamp=datetime.datetime.utcnow(),
        payload={"detail": "test"},
    )

    event_id = service.ingest(event)

    assert event_id == 100
    assert len(repository.saved) == 1
    saved = repository.saved[0]
    assert saved.camera_id == 1
    assert saved.event_type == "person"
    assert saved.severity == EventSeverity.LOW
    assert saved.payload["detail"] == "test"


def test_event_fusion_service_merges_recent_similar_event() -> None:
    existing = EventData(
        camera_id=1,
        camera_name="camera-1",
        event_type="person",
        severity=EventSeverity.LOW,
        score=0.1,
        timestamp=datetime.datetime.utcnow() - datetime.timedelta(seconds=20),
        payload={"old": True},
        id=42,
    )
    repository = DummyRepository(existing_event=existing)
    service = EventFusionService(repository=repository)
    incoming = EventData(
        camera_id=1,
        camera_name="camera-1",
        event_type="person",
        severity=EventSeverity.HIGH,
        score=0.9,
        timestamp=datetime.datetime.utcnow(),
        payload={"new": True},
    )

    event_id = service.ingest(incoming)

    assert event_id == 42
    assert len(repository.saved) == 1
    merged = repository.saved[0]
    assert merged.id == 42
    assert merged.severity == EventSeverity.HIGH
    assert merged.payload["old"] is True
    assert merged.payload["new"] is True
