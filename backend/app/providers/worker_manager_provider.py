from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.providers.worker_manager_impl import RealWorkerManagerAdapter
from app.settings import AppSettings, get_settings
from app.workers.manager import WorkerManager
from app.workers.protocols import WorkerManagerProtocol

logger = logging.getLogger(__name__)


class MockWorkerManager(WorkerManagerProtocol):
    """A lightweight mock/no-op WorkerManager used for testing and local dev.

    Implements WorkerManagerProtocol so it can be injected anywhere the
    protocol is required.
    """

    def __init__(self) -> None:
        self._running = False

    async def start_all(self) -> None:
        self._running = True

    async def stop_all(self) -> None:
        self._running = False

    async def start_camera(self, camera_identifier) -> bool:
        return True

    async def stop_camera(self, camera_identifier) -> bool:
        return True

    async def restart_camera(self, camera_identifier) -> bool:
        return True

    def status(self) -> Dict[int, Dict[str, Any]]:
        return {0: {"running": self._running}}

    def list_workers(self) -> List[int]:
        return []

    def get_worker(self, camera_id: int) -> Any:
        return None

    def health_check(self, camera_id: int | None = None) -> Dict[int, Dict[str, Any]] | Dict[str, Any]:
        if camera_id is None:
            return self.status()
        return {"running": self._running}

    async def shutdown(self) -> None:
        await self.stop_all()


def create_worker_manager(settings: AppSettings | None = None) -> WorkerManagerProtocol:
    """Factory that returns a WorkerManager implementation based on configuration.

    Args:
        settings: Optional AppSettings. If not provided, loaded from environment.

    Returns:
        An instance implementing WorkerManagerProtocol depending on settings.

    Raises:
        ValueError: if WORKER_MANAGER_TYPE contains an unsupported value.
    """
    if settings is None:
        settings = get_settings()

    wm_type = (settings.worker_manager_type or "").strip().lower()

    if wm_type in ("real", "production", "real_manager"):
        logger.info("Creating real WorkerManager (type=%s)", wm_type)
        real = WorkerManager()
        return RealWorkerManagerAdapter(real)

    if wm_type in ("mock", "test", "noop"):
        logger.info("Creating MockWorkerManager (type=%s)", wm_type)
        return MockWorkerManager()

    if wm_type in ("dev", "development"):
        # Development defaults to real but can be changed via settings
        logger.info("Development mode: creating real WorkerManager (type=%s)", wm_type)
        real = WorkerManager()
        return RealWorkerManagerAdapter(real)

    raise ValueError(f"Unsupported WORKER_MANAGER_TYPE: {settings.worker_manager_type}")
