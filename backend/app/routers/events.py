from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.event import Event
from app.models.user import User
from app.repositories.event_query_repository import EventQueryRepository
from app.schemas.event import EventResponse, EventTypesResponse, PaginatedEventsResponse

router = APIRouter(prefix="/events", tags=["events"])


def _to_response(event: Event) -> EventResponse:
    response = EventResponse.model_validate(event)
    response.linked = event.report_id is not None
    return response


@router.get("", response_model=PaginatedEventsResponse)
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    camera_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    linked_only: Optional[bool] = Query(None),
    report_id: Optional[int] = Query(None),
    sort_by: str = Query("timestamp"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> PaginatedEventsResponse:
    repo = EventQueryRepository(db)
    events, total = repo.list(
        page=page,
        page_size=page_size,
        camera_id=camera_id,
        event_type=event_type,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
        search=search,
        linked_only=linked_only,
        report_id=report_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return PaginatedEventsResponse(items=[_to_response(e) for e in events], total=total, page=page, page_size=page_size)


@router.get("/types", response_model=EventTypesResponse)
def list_event_types(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> EventTypesResponse:
    return EventTypesResponse(types=EventQueryRepository(db).distinct_event_types())


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> EventResponse:
    event = EventQueryRepository(db).get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return _to_response(event)
