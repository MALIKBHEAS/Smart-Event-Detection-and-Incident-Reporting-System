from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from ..db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(64), nullable=False, index=True)  # new_event | new_incident | system
    message = Column(String(512), nullable=False)
    severity = Column(String(32), nullable=False, default="low")
    related_type = Column(String(32), nullable=True)  # event | report
    related_id = Column(Integer, nullable=True)
    read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
