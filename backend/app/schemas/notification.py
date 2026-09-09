from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    message: str
    severity: str
    related_type: Optional[str]
    related_id: Optional[int]
    read: bool
    created_at: Optional[datetime]


class PaginatedNotificationsResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
