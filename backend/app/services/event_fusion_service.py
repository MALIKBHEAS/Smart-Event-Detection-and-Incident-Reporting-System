"""Event Fusion service responsible for ingesting, normalizing and persisting fused events."""
from __future__ import annotations

import logging
from dataclasses import replace

from app.domain.event import EventData, EventSeverity
from app.repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)


class EventFusionService:
    """Service that receives detection outputs, fuses them into domain events, and stores them."""

    def __init__(self, repository: EventRepository | None = None) -> None:
        self.repository = repository or EventRepository()

    def ingest(self, event_data: EventData) -> int | None:
        """Ingest an EventData object, optionally fusing with a recent similar event."""
        try:
            normalized = self._normalize_event(event_data)
            existing = self.repository.find_recent_by_camera_and_type(
                normalized.camera_id,
                normalized.event_type,
                within_seconds=30,
            )
            if existing is not None:
                fused = self._merge_events(existing, normalized)
                return self.repository.save(fused)
            return self.repository.save(normalized)
        except Exception:
            logger.exception("Failed to ingest event into EventFusionService")
            return None

    def _normalize_event(self, event_data: EventData) -> EventData:
        severity = event_data.severity
        if isinstance(severity, str):
            try:
                severity = EventSeverity(severity)
            except ValueError:
                severity = EventSeverity.from_score(event_data.score)
        if not isinstance(severity, EventSeverity):
            severity = EventSeverity.from_score(event_data.score)
        return replace(event_data, severity=severity)

    def _merge_events(self, existing: EventData, incoming: EventData) -> EventData:
        chosen_severity = (
            existing.severity
            if existing.severity.rank >= incoming.severity.rank
            else incoming.severity
        )
        payload = dict(existing.payload)
        payload.update(incoming.payload)
        merged_score = max(existing.score, incoming.score)
        merged_timestamp = max(existing.timestamp, incoming.timestamp)
        # Prefer an existing report association; fall back to any incoming association
        merged_report_id = existing.report_id if getattr(existing, 'report_id', None) is not None else incoming.report_id
        return EventData(
            id=existing.id,
            camera_id=existing.camera_id,
            camera_name=incoming.camera_name or existing.camera_name,
            event_type=existing.event_type,
            severity=chosen_severity,
            score=merged_score,
            timestamp=merged_timestamp,
            payload=payload,
            source=incoming.source or existing.source,
            screenshot_path=incoming.screenshot_path or existing.screenshot_path,
            report_id=merged_report_id,
        )
