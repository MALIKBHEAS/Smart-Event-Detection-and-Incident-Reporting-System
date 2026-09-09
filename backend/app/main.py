"""FastAPI application entrypoint wiring WorkerManager into lifecycle using
FastAPI's lifespan context manager and dependency injection.

This module provides a single app instance that initializes WorkerManager on
startup and ensures graceful shutdown. Expose DI-friendly endpoints that accept
WorkerManager via FastAPI Depends().
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

import cv2
import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth.dependencies import get_current_user, get_current_user_optional, require_role
from app.auth.router import router as auth_router
from app.auth.security import TokenType, decode_token
from app.db.session import SessionLocal
from app.dependencies.worker_manager import get_worker_manager
from app.intelligence.api.analytics_router import router as analytics_router
from app.models.user import User
from app.notifications.router import router as notifications_router
from app.routers import cameras_router, events_router, reports_router, users_router
from app.routers.settings import router as settings_router
from app.routers.health_components_router import router as health_components_router
from app.services.database_health_service import DatabaseHealthService
from app.services.event_fusion_service import EventFusionService
from app.services.health_service import HealthService
from app.services.system_metrics_service import SystemMetricsService
from app.settings import AppSettings, get_settings
from app.workers.protocols import WorkerManagerProtocol

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan. Create WorkerManager, start workers, and ensure
    shutdown cleanup.

    The manager is attached to app.state.worker_manager so it can be injected
    via a dependency.
    """
    logger.info("Initializing application lifespan")
    settings = AppSettings()
    app.state.settings = settings

    import asyncio

    from app.notifications.manager import connection_manager

    connection_manager.bind_loop(asyncio.get_running_loop())

    # record the process start time for uptime calculations
    import time

    app.state.start_time = time.time()
    app.state.version = getattr(settings, 'version', '1.0.0')

    logger.info(
        "Loaded configuration: app_env=%s worker_manager_type=%s version=%s",
        settings.app_env,
        settings.worker_manager_type,
        app.state.version,
    )

    app.state.event_service = EventFusionService()
    logger.info("Initialized EventFusionService")

    # Instantiate WorkerManager via the provider so different implementations can be selected
    from app.providers.worker_manager_provider import create_worker_manager

    manager = create_worker_manager(settings)
    app.state.worker_manager = manager

    # Build the health service after initialization so the /health endpoint
    # can delegate all health logic to a dedicated business service.
    from app.db import session as db_session

    db_health_service = DatabaseHealthService(
        engine=db_session.engine,
        enabled=bool(settings.database_url),
    )
    app.state.health_service = HealthService(
        database_health_service=db_health_service,
        worker_manager=manager,
        event_fusion_service=app.state.event_service,
        version=app.state.version,
        start_time=app.state.start_time,
    )

    try:
        try:
            await manager.start_all()
            logger.info("WorkerManager started and camera workers initiated")
        except Exception:
            logger.exception("WorkerManager failed to start all workers during app startup")
        yield
    finally:
        logger.info("Lifespan cleanup: stopping WorkerManager and workers")
        try:
            await manager.stop_all()
            logger.info("WorkerManager stopped all workers")
        except Exception:
            logger.exception("Error while stopping WorkerManager during lifespan shutdown")


app = FastAPI(title="Smart Event Detection - Backend", lifespan=lifespan)
app.include_router(cameras_router)
app.include_router(reports_router)
app.include_router(events_router)
app.include_router(users_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(notifications_router)
app.include_router(settings_router)
app.include_router(health_components_router)


@app.get("/health", response_class=JSONResponse)
async def health(request: Request) -> JSONResponse:
    """Return overall application health."""
    health_service = getattr(request.app.state, "health_service", None)
    if health_service is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "version": getattr(request.app.state, 'version', '1.0.0'),
                "uptime": None,
                "services": {
                    "database": {"status": "unavailable", "latency_ms": None},
                    "worker_manager": {"status": "unavailable"},
                    "event_fusion": {"status": "unavailable"},
                },
                "workers": {"active": 0},
            },
        )
    return JSONResponse(content=health_service.get_health())


def draw_detection_overlays(frame: Any, tracked_objects: list) -> Any:
    """Draw real detection/tracking overlays (bbox, track id, class,
    confidence) onto a copy of the frame. No-op (returns the original
    frame) if there's nothing to draw -- never fabricates boxes."""
    if not tracked_objects:
        return frame
    annotated = frame.copy()
    for track in tracked_objects:
        try:
            x1, y1, x2, y2 = (int(v) for v in track.bounding_box)
        except Exception:
            continue
        color = (46, 204, 113)  # BGR, matches the app's "live" green
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        confidence = track.confidence if track.confidence else 0.0
        label = f"#{track.track_id} {track.class_name} {confidence:.0%}"
        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_y = max(y1, text_h + 6)
        cv2.rectangle(annotated, (x1, label_y - text_h - 6), (x1 + text_w + 6, label_y), color, -1)
        cv2.putText(annotated, label, (x1 + 3, label_y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return annotated


@app.get("/cameras/{camera_id}/stream")
async def stream_camera(
    camera_id: int,
    manager: WorkerManagerProtocol = Depends(get_worker_manager),
    token: str | None = Query(None),
    header_user: User | None = Depends(get_current_user_optional),
) -> StreamingResponse:
    """MJPEG stream of the camera's latest frame, annotated with real-time
    detection/tracking overlays (bounding box, track id, class, confidence)
    from the worker's own pipeline output -- nothing here is synthesized;
    if the worker has no current tracked objects, the frame is streamed
    unannotated.

    Accepts auth via the normal Authorization header OR a `token` query
    param -- browser <img>/<video> elements can't set custom headers, so
    the query-param path (same JWT, same validation) is what the frontend
    actually uses for this endpoint. Mirrors /ws/notifications.
    """
    user = header_user
    if user is None:
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            settings = get_settings()
            payload = decode_token(token, settings=settings, expected_type=TokenType.ACCESS)
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        session = SessionLocal()
        try:
            user = session.get(User, int(payload["sub"]))
        finally:
            session.close()
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Account no longer available")

    worker = manager.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"No running worker for camera {camera_id}")

    async def _mjpeg_generator():
        boundary = b"--frame"
        last_ts = None
        while True:
            frame = getattr(worker, "_latest_frame", None)
            ts = getattr(worker, "_last_frame_ts", None)
            if frame is not None and ts != last_ts:
                last_ts = ts
                tracked_objects = getattr(worker, "_latest_tracked_objects", [])
                annotated = draw_detection_overlays(frame, tracked_objects)
                ok, buf = cv2.imencode(".jpg", annotated)
                if ok:
                    yield (
                        boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                        + str(len(buf)).encode() + b"\r\n\r\n" + buf.tobytes() + b"\r\n"
                    )
            await asyncio.sleep(0.1)

    return StreamingResponse(_mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/health/workers", response_class=JSONResponse)
async def workers_health(manager: WorkerManagerProtocol = Depends(get_worker_manager)) -> JSONResponse:
    """Return status for all managed camera workers."""
    status = manager.status()
    return JSONResponse(content={"workers": status})


@app.get("/system/metrics")
async def system_metrics(
    manager: WorkerManagerProtocol = Depends(get_worker_manager),
    _user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Real system resource + pipeline metrics (CPU/RAM/disk/GPU/workers).
    See SystemMetricsService for exactly which fields are real vs. reported
    as unavailable (never faked)."""
    return SystemMetricsService(manager).get_metrics()


_can_operate_workers = require_role("Admin", "Security Operator")


@app.post("/workers/start/{camera_id}")
async def start_camera(
    camera_id: int,
    manager: WorkerManagerProtocol = Depends(get_worker_manager),
    _user: User = Depends(_can_operate_workers),
) -> Dict[str, Any]:
    """Start a worker for the given camera id."""
    ok = await manager.start_camera(camera_id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Failed to start worker for camera {camera_id}")
    return {"started": True, "camera_id": camera_id}


@app.post("/workers/stop/{camera_id}")
async def stop_camera(
    camera_id: int,
    manager: WorkerManagerProtocol = Depends(get_worker_manager),
    _user: User = Depends(_can_operate_workers),
) -> Dict[str, Any]:
    """Stop a worker for the given camera id."""
    ok = await manager.stop_camera(camera_id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Failed to stop worker for camera {camera_id}")
    return {"stopped": True, "camera_id": camera_id}
