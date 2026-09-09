"""Event model."""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=True)
    # Link to report (nullable for backward compatibility)
    report_id = Column(Integer, ForeignKey('reports.id', ondelete='SET NULL'), nullable=True, index=True)

    type = Column(String(128), nullable=False, index=True)
    severity = Column(String(32), nullable=False, default='low')
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    payload = Column(JSON, nullable=True)

    # Relationship to allow access to associated Report from an Event instance
    report = relationship('Report', back_populates='linked_events')
