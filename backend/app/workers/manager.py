"""Worker manager for RTSPDetectionWorker instances.

This module provides WorkerManager which can start/stop workers for cameras
stored in the database and query their status.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, cast

from ..db.session import SessionLocal
from ..models.camera import Camera
from .tracker import create_tracker
from .worker import RTSPDetectionWorker, WorkerConfig

logger = logging.getLogger(__name__)


class WorkerManager:
    """Manage multiple RTSPDetectionWorker instances.

    Responsibilities:
    - Load camera configurations from the database (Camera model)
    - Create and start/stop RTSPDetectionWorker instances per camera
    - Provide status information for managed workers

    Notes:
    - All start/stop operations are asynchronous because RTSPDetectionWorker
      exposes async start/stop methods.
    - Camera lookup happens against a fresh SQLAlchemy session created from
      SessionLocal. Sessions are closed after each operation to avoid leaking
      connections.
    """

    def __init__(self, session_factory=SessionLocal) -> None:
        """Initialize the manager.

        Args:
            session_factory: Callable that returns a new SQLAlchemy Session
                (defaults to app.db.session.SessionLocal).
        """
        self._session_factory = session_factory
        # map camera id -> RTSPDetectionWorker
        self._workers: Dict[int, RTSPDetectionWorker] = {}
        # protect _workers map with an asyncio lock created lazily
        self._lock: Optional[asyncio.Lock] = None

    async def _ensure_lock(self) -> asyncio.Lock:
        """Create an asyncio lock when a running event loop is available."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _build_tracker_from_config(self, cam: Camera) -> object:
        """Create a tracker for a given camera using camera metadata and env vars.

        Camera.metadata may include a dict with tracker settings, for example:
          metadata: {"tracker": {"use_byte": true, "max_disappeared": 30, "max_distance": 50}}

        Environment variables that influence tracker creation:
          TRACKER_USE_BYTE (true|false)
          TRACKER_MAX_DISAPPEARED
          TRACKER_MAX_DISTANCE
        """
        import os

        env_use_byte = os.getenv('TRACKER_USE_BYTE')
        env_max_dis = os.getenv('TRACKER_MAX_DISAPPEARED')
        env_max_dist = os.getenv('TRACKER_MAX_DISTANCE')

        tracker_meta = getattr(cam, 'tracker_config', None)
        if not isinstance(tracker_meta, dict):
            tracker_meta = {}

        if not tracker_meta:
            metadata = getattr(cam, 'metadata', None)
            if isinstance(metadata, dict):
                tracker_meta = metadata.get('tracker', {}) or {}

        if 'use_byte' in tracker_meta:
            use_byte = bool(tracker_meta.get('use_byte'))
        elif env_use_byte is not None:
           use_byte = env_use_byte.lower() == 'true'
        else:
           use_byte = True

        try:
            max_disappeared = int(tracker_meta.get('max_disappeared', env_max_dis if env_max_dis else 50))
        except Exception:
            max_disappeared = 50
        try:
            max_distance = float(tracker_meta.get('max_distance', env_max_dist if env_max_dist else 50.0))
        except Exception:
            max_distance = 50.0

        tracker_kwargs = {'max_disappeared': max_disappeared, 'max_distance': max_distance}

        try:
            tracker = create_tracker(use_byte=use_byte, **tracker_kwargs)
            # Log whether ByteTrack backend was actually initialized
            backend_initialized = getattr(tracker, '_backend', None) is not None
            if backend_initialized:
                logger.info("ByteTrack initialized for camera '%s' (id=%s).", cam.name, cam.id)
            else:
                logger.info("ByteTrack not found for camera '%s' (id=%s); using fallback tracker.", cam.name, cam.id)
            return tracker
        except Exception as exc:
            logger.exception("Failed to create tracker for camera %s (id=%s); falling back. Error: %s", cam.name, cam.id, exc)
            return create_tracker(use_byte=False, **tracker_kwargs)

    async def start_all(self) -> None:
        """Start workers for all active cameras found in the database.

        Cameras with an existing running worker are skipped.
        """
        logger.debug("Starting all active camera workers")
        session = self._session_factory()
        try:
            cameras: List[Camera] = session.query(Camera).filter(Camera.enabled == True).all()
        finally:
            session.close()

        async with await self._ensure_lock():
            for cam in cameras:
                camera_id = int(cast(int, cam.id))
                if camera_id in self._workers:
                    logger.debug("Worker already exists for camera %s (%d)", cam.name, camera_id)
                    continue
                detection_config = getattr(cam, 'detector_config', {}) or {}
                config = WorkerConfig(
                    source=cam.rtsp_url,
                    camera_id=camera_id,
                    camera_name=str(cast(str, cam.name)),
                    detector_name=detection_config.get('detector_name'),
                    fps=float(detection_config.get('fps', 5.0)),
                    confidence_threshold=float(detection_config.get('confidence_threshold', 0.5)),
                    frame_skip=int(detection_config.get('frame_skip', 0)),
                    device=str(detection_config.get('device')) if detection_config.get('device') is not None else None,
                    event_detectors=detection_config.get('event_detectors', []),
                )
                tracker = self._build_tracker_from_config(cam)
                worker = RTSPDetectionWorker(config, tracker=tracker)
                try:
                    await worker.start()
                    self._workers[camera_id] = worker
                    logger.info("Started worker for camera %s (%d)", cam.name, camera_id)
                except Exception:
                    logger.exception("Failed to start worker for camera %s (%d)", cam.name, camera_id)

    async def stop_all(self) -> None:
        """Stop all running workers and clear the worker map."""
        logger.debug("Stopping all camera workers")
        async with await self._ensure_lock():
            # create list to avoid mutation during iteration
            workers = list(self._workers.items())
            for cam_id, worker in workers:
                try:
                    await worker.stop()
                    logger.info("Stopped worker for camera id %s", cam_id)
                except Exception:
                    logger.exception("Error stopping worker for camera id %s", cam_id)
            self._workers.clear()

    async def start_camera(self, camera_identifier: Union[int, str]) -> bool:
        """Start worker for a single camera.

        Args:
            camera_identifier: camera id (int) or camera name (str)

        Returns:
            True if a worker was started (or already running), False if camera
            not found or failed to start.
        """
        session = self._session_factory()
        try:
            if isinstance(camera_identifier, int):
                cam = session.query(Camera).filter(Camera.id == camera_identifier).one_or_none()
            else:
                cam = session.query(Camera).filter(Camera.name == camera_identifier).one_or_none()
        finally:
            session.close()

        if cam is None:
            logger.warning("Camera not found: %s", camera_identifier)
            return False

        async with await self._ensure_lock():
            camera_id = int(cast(int, cam.id))
            if camera_id in self._workers:
                logger.debug("Worker already running for camera %s (%d)", cam.name, camera_id)
                return True
            detection_config = getattr(cam, 'detector_config', {}) or {}
            config = WorkerConfig(
                source=cam.rtsp_url,
                camera_id=camera_id,
                camera_name=str(cast(str, cam.name)),
                detector_name=detection_config.get('detector_name'),
                fps=float(detection_config.get('fps', 5.0)),
                confidence_threshold=float(detection_config.get('confidence_threshold', 0.5)),
                frame_skip=int(detection_config.get('frame_skip', 0)),
                device=str(detection_config.get('device')) if detection_config.get('device') is not None else None,
                event_detectors=detection_config.get('event_detectors', []),
            )
            tracker = self._build_tracker_from_config(cam)
            worker = RTSPDetectionWorker(config, tracker=tracker)
            try:
                await worker.start()
                self._workers[camera_id] = worker
                logger.info("Started worker for camera %s (%d)", cam.name, camera_id)
                return True
            except Exception:
                logger.exception("Failed to start worker for camera %s (%d)", cam.name, camera_id)
                return False

    async def stop_camera(self, camera_identifier: Union[int, str]) -> bool:
        """Stop worker for a single camera.
 
        Args:
            camera_identifier: camera id (int) or camera name (str)
 
        Returns:
            True if a worker was stopped (or didn't exist), False if camera
            not found in DB.
        """
        session = self._session_factory()
        try:
            if isinstance(camera_identifier, int):
                cam = session.query(Camera).filter(Camera.id == camera_identifier).one_or_none()
            else:
                cam = session.query(Camera).filter(Camera.name == camera_identifier).one_or_none()
        finally:
            session.close()

        if cam is None:
            logger.warning("Camera not found: %s", camera_identifier)
            return False

        async with await self._ensure_lock():
            camera_id = int(cast(int, cam.id))
            worker = self._workers.get(camera_id)
            if not worker:
                logger.debug("No running worker for camera %s (%d)", cam.name, camera_id)
                return True
            try:
                await worker.stop()
                del self._workers[camera_id]
                logger.info("Stopped worker for camera %s (%d)", cam.name, camera_id)
                return True
            except Exception:
                logger.exception("Failed to stop worker for camera %s (%d)", cam.name, camera_id)
                return False

    async def restart_camera(self, camera_identifier: Union[int, str]) -> bool:
        """Restart a running camera worker by stopping it and starting it again.
 
        If the camera is not currently running, this method behaves like
        start_camera().
        """
        session = self._session_factory()
        try:
            if isinstance(camera_identifier, int):
                cam = session.query(Camera).filter(Camera.id == camera_identifier).one_or_none()
            else:
                cam = session.query(Camera).filter(Camera.name == camera_identifier).one_or_none()
        finally:
            session.close()

        if cam is None:
            logger.warning("Camera not found: %s", camera_identifier)
            return False

        async with await self._ensure_lock():
            camera_id = int(cast(int, cam.id))
            existing = self._workers.pop(camera_id, None)
            if existing is not None:
                try:
                    await existing.stop()
                except Exception:
                    logger.exception("Failed to stop existing worker for camera %s (%d) during restart", cam.name, camera_id)

            detection_config = getattr(cam, 'detector_config', {}) or {}
            if isinstance(detection_config, dict):
                event_detectors = detection_config.get('event_detectors', [])
            else:
                event_detectors = []

            config = WorkerConfig(
                source=cam.rtsp_url,
                camera_id=camera_id,
                camera_name=str(cast(str, cam.name)),
                detector_name=detection_config.get('detector_name') if isinstance(detection_config, dict) else None,
                fps=float(detection_config.get('fps', 5.0)) if isinstance(detection_config, dict) else 5.0,
                confidence_threshold=float(detection_config.get('confidence_threshold', 0.5)) if isinstance(detection_config, dict) else 0.5,
                frame_skip=int(detection_config.get('frame_skip', 0)) if isinstance(detection_config, dict) else 0,
                device=str(detection_config.get('device')) if isinstance(detection_config, dict) and detection_config.get('device') is not None else None,
                event_detectors=event_detectors,
            )
            tracker = self._build_tracker_from_config(cam)
            worker = RTSPDetectionWorker(config, tracker=tracker)
            try:
                await worker.start()
                self._workers[camera_id] = worker
                logger.info("Restarted worker for camera %s (%d)", cam.name, camera_id)
                return True
            except Exception:
                logger.exception("Failed to restart worker for camera %s (%d)", cam.name, camera_id)
                return False

    def get_worker(self, camera_id: int) -> Optional[RTSPDetectionWorker]:
        """Return the running worker for a camera, if any (used by the
        MJPEG streaming endpoint to read the latest raw frame)."""
        return self._workers.get(camera_id)

    def status(self) -> Dict[int, Dict[str, Any]]:
        """Return a map camera_id -> health/status for all managed cameras.

        The returned structure contains at least the keys:
          - "running": bool
          - "last_seen": Optional[float]
        If a camera is not currently managed, its status will be {"running": False}.
        """
        result: Dict[int, Dict[str, Any]] = {}
        # no need to await lock for read-only shallow snapshot
        for cam_id, worker in list(self._workers.items()):
            try:
                result[cam_id] = worker.health_check()
            except Exception:
                logger.exception("Failed to get health for worker %s", cam_id)
                result[cam_id] = {"running": False}
        return result
