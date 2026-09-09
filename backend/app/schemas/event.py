from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: Optional[int]
    report_id: Optional[int]
    type: str
    severity: str
    timestamp: Optional[datetime]
    payload: Optional[Dict[str, Any]]
    # Derived, not a real "status" column on the model (Event has none) --
    # the one honest status-like signal available is whether this detection
    # was fused into an incident report yet.
    linked: bool = False


class PaginatedEventsResponse(BaseModel):
    items: List[EventResponse]
    total: int
    page: int
    page_size: int


class EventTypesResponse(BaseModel):
    types: List[str]
