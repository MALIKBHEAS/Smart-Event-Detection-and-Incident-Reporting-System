"""Camera model."""
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import synonym

from ..db.base import Base


class Camera(Base):
    __tablename__ = 'cameras'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    rtsp_url = Column(String(1024), nullable=False)
    location = Column(String(255), nullable=True)
    # 'metadata' is a reserved attribute on Declarative Base; expose it as 'metadata_' in Python
    metadata_ = Column('metadata', JSON, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    is_active = synonym('enabled')
    detector_config = Column(JSON, nullable=True)
    tracker_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Camera id={self.id!r} name={self.name!r} enabled={self.enabled!r}>"
