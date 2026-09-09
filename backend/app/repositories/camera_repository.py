from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.camera import Camera


class CameraRepository:
    """Repository for camera persistence operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> List[Camera]:
        return self._session.query(Camera).order_by(Camera.id).all()

    def get(self, camera_id: int) -> Optional[Camera]:
        return self._session.get(Camera, camera_id)

    def get_by_name(self, name: str) -> Optional[Camera]:
        return self._session.query(Camera).filter(Camera.name == name).one_or_none()

    def add(self, camera: Camera) -> Camera:
        self._session.add(camera)
        self._session.flush()
        return camera

    def delete(self, camera: Camera) -> None:
        self._session.delete(camera)
