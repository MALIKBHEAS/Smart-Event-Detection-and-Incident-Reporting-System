"""Read-only Event querying for the Events page: filter/search/sort/pagination.

Deliberately separate from EventRepository (app/repositories/event_repository.py),
which self-manages sessions because it's called from background worker
threads to persist fused events. This class is session-injected (mirrors
ReportRepository) because it's only ever used within a single FastAPI
request lifecycle for reads.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.models.event import Event

SORTABLE_FIELDS = {
    "timestamp": Event.timestamp,
    "type": Event.type,
    "severity": Event.severity,
}


class EventQueryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, event_id: int) -> Optional[Event]:
        return self._session.get(Event, event_id)

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        camera_id: Optional[int] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        search: Optional[str] = None,
        linked_only: Optional[bool] = None,
        report_id: Optional[int] = None,
        sort_by: str = "timestamp",
        sort_dir: str = "desc",
    ) -> Tuple[List[Event], int]:
        query = self._session.query(Event)

        if camera_id is not None:
            query = query.filter(Event.camera_id == camera_id)
        if event_type:
            query = query.filter(Event.type == event_type)
        if severity:
            query = query.filter(Event.severity == severity)
        if start_time is not None:
            query = query.filter(Event.timestamp >= start_time)
        if end_time is not None:
            query = query.filter(Event.timestamp <= end_time)
        if report_id is not None:
            query = query.filter(Event.report_id == report_id)
        if linked_only is True:
            query = query.filter(Event.report_id.isnot(None))
        elif linked_only is False:
            query = query.filter(Event.report_id.is_(None))
        if search:
            # payload is JSON; type is the closest indexed/searchable text field.
            query = query.filter(Event.type.ilike(f"%{search}%"))

        total = query.count()

        sort_column = SORTABLE_FIELDS.get(sort_by, Event.timestamp)
        order_fn = asc if sort_dir == "asc" else desc
        query = query.order_by(order_fn(sort_column))  # type: ignore[arg-type]

        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        return rows, total

    def distinct_event_types(self) -> List[str]:
        rows = self._session.query(Event.type).distinct().all()
        return sorted({row[0] for row in rows if row[0]})
