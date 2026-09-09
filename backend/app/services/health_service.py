"""Application health aggregation service."""
from __future__ import annotations

import time
from typing import Any

from app.services.database_health_service import DatabaseHealthService
from app.services.event_fusion_service import EventFusionService
from app.workers.protocols import WorkerManagerProtocol


class HealthService:
    """Aggregate health information from application subsystems."""

    def __init__(
        self,
        database_health_service: DatabaseHealthService,
        worker_manager: WorkerManagerProtocol | None,
        event_fusion_service: EventFusionService | None,
        version: str = "1.0.0",
        start_time: float | None = None,
    ) -> None:
        self._database_health_service = database_health_service
        self._worker_manager = worker_manager
        self._event_fusion_service = event_fusion_service
        self._version = version
        self._start_time = start_time

    def _worker_manager_status(self) -> dict[str, Any]:
        if self._worker_manager is None:
            return {"status": "unavailable"}
        try:
            self._worker_manager.list_workers()
            return {"status": "running"}
        except Exception:
            return {"status": "degraded"}

    def _event_fusion_status(self) -> dict[str, Any]:
        if self._event_fusion_service is None:
            return {"status": "unavailable"}
        return {"status": "running"}

    def get_health(self) -> dict[str, Any]:
        database_status = self._database_health_service.check()
        worker_manager_status = self._worker_manager_status()
        event_fusion_status = self._event_fusion_status()

        services = {
            "database": database_status,
            "worker_manager": worker_manager_status,
            "event_fusion": event_fusion_status,
        }

        acceptable = {"running", "connected", "not_configured"}
        overall_status = (
            "healthy"
            if all(service.get("status") in acceptable for service in services.values())
            else "degraded"
        )

        uptime = None
        if self._start_time is not None:
            uptime_secs = time.time() - float(self._start_time)
            uptime = f"{uptime_secs:.2f}s"

        workers = {"active": len(self._worker_manager.list_workers())} if self._worker_manager is not None else {"active": 0}

        return {
            "status": overall_status,
            "version": self._version,
            "uptime": uptime,
            "services": services,
            "workers": workers,
        }

    def is_ready(self) -> bool:
        return bool(self.get_health()["status"] == "healthy")

    def is_alive(self) -> bool:
        return (self._worker_manager is not None) and (self._event_fusion_service is not None)
