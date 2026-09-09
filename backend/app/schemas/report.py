from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

VALID_STATUSES = {"open", "in_progress", "resolved", "closed"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


class ReportBase(BaseModel):
    title: str = Field(..., max_length=255)
    summary: str = Field(..., max_length=2048)
    details: Optional[str] = None
    incident_type: Optional[str] = Field(None, max_length=128)
    severity: str = Field("low", max_length=32)
    status: str = Field("open", max_length=32)
    camera_id: Optional[int] = None
    occurred_at: Optional[datetime] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class ReportCreate(ReportBase):
    pass


class ReportUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    summary: Optional[str] = Field(None, max_length=2048)
    details: Optional[str] = None
    incident_type: Optional[str] = Field(None, max_length=128)
    severity: Optional[str] = Field(None, max_length=32)
    status: Optional[str] = Field(None, max_length=32)
    camera_id: Optional[int] = None
    occurred_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class ReportResponse(ReportBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    event_count: int = 0


class PaginatedReportsResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    page: int
    page_size: int
