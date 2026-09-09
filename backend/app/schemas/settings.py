from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detection_confidence_threshold: float
    evidence_retention_days: int
    notify_on_new_event: bool
    notify_on_new_incident: bool
    updated_at: Optional[datetime]


class SettingsUpdate(BaseModel):
    detection_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence_retention_days: Optional[int] = Field(None, ge=1, le=3650)
    notify_on_new_event: Optional[bool] = None
    notify_on_new_incident: Optional[bool] = None
