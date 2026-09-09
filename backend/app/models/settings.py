from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer

from ..db.base import Base


class AppSettingsRow(Base):
    """Single-row settings table (id is always 1). Deliberately minimal --
    only settings that are actually read/applied somewhere in the backend."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    detection_confidence_threshold = Column(Float, nullable=False, default=0.5)
    evidence_retention_days = Column(Integer, nullable=False, default=30)
    notify_on_new_event = Column(Boolean, nullable=False, default=True)
    notify_on_new_incident = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
