"""Report model."""
# Additional imports preserved separately so original imports remain unchanged
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base


class Report(Base):
    __tablename__ = 'reports'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(String(2048), nullable=False)
    # Free-text field for longer incident details that may not fit into `summary`
    details = Column(Text, nullable=True)
    # Categorization and severity for filtering and routing
    incident_type = Column(String(128), nullable=True, index=True)
    severity = Column(String(32), nullable=False, default='low', index=True)
    status = Column(String(32), nullable=False, default='open', index=True)

    # References to users and camera involved in the report. Use ondelete to avoid orphaned references.
    reporter_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    assigned_to_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey('cameras.id', ondelete='SET NULL'), nullable=True, index=True)

    # When the incident actually occurred and when it was resolved (if applicable)
    occurred_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Keep the existing events JSON column for compatibility with current ingestion pipelines
    events = Column(JSON, nullable=True)

    # Attachments, tags and audit timestamps
    attachments = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ORM relationships (do not change other models). Use explicit foreign_keys where there are two FKs to the same table.
    reporter = relationship('User', foreign_keys=[reporter_id], backref='reported_reports')
    assigned_to = relationship('User', foreign_keys=[assigned_to_id], backref='assigned_reports')
    camera = relationship('Camera', backref='reports')
    # Relationship to Event model; name avoids collision with 'events' JSON column
    linked_events = relationship('Event', back_populates='report', foreign_keys='Event.report_id')

    __table_args__ = (
        Index('ix_reports_created_status', 'created_at', 'status'),
    )

    def __repr__(self):
        return f"<Report id={self.id!r} title={self.title!r} status={self.status!r} severity={self.severity!r}>"
