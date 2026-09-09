from __future__ import annotations

import logging
from typing import Any, Dict, Optional, cast

from sqlalchemy.orm import Session

from app.models.camera import Camera
from app.repositories.camera_repository import CameraRepository
from app.schemas.camera import CameraCreate, CameraUpdate
from app.workers.protocols import WorkerManagerProtocol

logger = logging.getLogger(__name__)


class CameraNotFoundError(Exception):
    pass


class CameraService:
    """Business logic for camera management."""

    def __init__(
        self,
        session: Session,
        worker_manager: WorkerManagerProtocol | None = None,
    ) -> None:
        self._session = session
        self._repository = CameraRepository(session)
        self._worker_manager = worker_manager

    def list_cameras(self) -> list[Camera]:
        return self._repository.list()

    def get_camera(self, camera_id: int) -> Camera:
        camera = self._repository.get(camera_id)
        if camera is None:
            raise CameraNotFoundError(f"Camera not found: {camera_id}")
        return camera

    async def create_camera(self, camera_in: CameraCreate) -> Camera:
        camera = Camera(
            name=camera_in.name,
            rtsp_url=camera_in.rtsp_url,
            location=camera_in.location,
            enabled=camera_in.enabled,
            detector_config=camera_in.detector_config,
            tracker_config=camera_in.tracker_config,
        )
        self._repository.add(camera)
        self._session.commit()
        self._session.refresh(camera)

        if camera.enabled and self._worker_manager is not None:
            worker_manager = self._worker_manager
            try:
                await worker_manager.start_camera(camera.id)
            except Exception:
                logger.exception("Failed starting worker for enabled camera %s", camera.id)
        return camera

    async def update_camera(self, camera_id: int, camera_in: CameraUpdate) -> Camera:
        camera = self.get_camera(camera_id)
        previous_state = {
            "enabled": bool(camera.enabled),
            "rtsp_url": cast(str, camera.rtsp_url),
            "detector_config": cast(Optional[Dict[str, Any]], camera.detector_config),
            "tracker_config": cast(Optional[Dict[str, Any]], camera.tracker_config),
        }

        if camera_in.name is not None:
            setattr(camera, "name", camera_in.name)
        if camera_in.rtsp_url is not None:
            setattr(camera, "rtsp_url", camera_in.rtsp_url)
        if camera_in.location is not None:
            setattr(camera, "location", camera_in.location)
        if camera_in.enabled is not None:
            setattr(camera, "enabled", camera_in.enabled)
        if camera_in.detector_config is not None:
            setattr(camera, "detector_config", camera_in.detector_config)
        if camera_in.tracker_config is not None:
            setattr(camera, "tracker_config", camera_in.tracker_config)

        self._session.add(camera)
        self._session.commit()
        self._session.refresh(camera)

        if self._worker_manager is not None:
            worker_manager = self._worker_manager
            await self._apply_worker_changes(camera, previous_state)

        return camera

    async def delete_camera(self, camera_id: int) -> None:
        camera = self.get_camera(camera_id)
        if self._worker_manager is not None:
            worker_manager = self._worker_manager
            try:
                await worker_manager.stop_camera(camera.id)
            except Exception:
                logger.exception("Failed stopping worker for camera %s before deletion", camera.id)

        self._repository.delete(camera)
        self._session.commit()

    async def _apply_worker_changes(self, camera: Camera, previous_state: Dict[str, Any]) -> None:
        enabled_changed = camera.enabled != previous_state["enabled"]
        config_changed = any(
            camera_value != previous_state[key]
            for key, camera_value in {
                "rtsp_url": camera.rtsp_url,
                "detector_config": camera.detector_config,
                "tracker_config": camera.tracker_config,
            }.items()
        )

        worker_manager = self._worker_manager
        if worker_manager is None:
            return

        if enabled_changed:
            if camera.enabled:
                await worker_manager.start_camera(camera.id)
            else:
                await worker_manager.stop_camera(camera.id)
            return

        if camera.enabled and config_changed:
            try:
                await worker_manager.restart_camera(camera.id)
            except Exception:
                logger.exception("Failed restarting worker for camera %s after config update", camera.id)
