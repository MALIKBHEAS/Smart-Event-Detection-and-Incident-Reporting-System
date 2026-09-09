from __future__ import annotations

from typing import Any, Dict, List

from app.workers.manager import WorkerManager
from app.workers.protocols import WorkerManagerProtocol


class RealWorkerManagerAdapter(WorkerManagerProtocol):
    """Adapter that wraps the existing WorkerManager to satisfy the
    WorkerManagerProtocol without modifying the original class.
    """

    def __init__(self, delegate: WorkerManager) -> None:
        self._delegate = delegate

    async def start_all(self) -> None:
        await self._delegate.start_all()

    async def stop_all(self) -> None:
        await self._delegate.stop_all()

    async def start_camera(self, camera_identifier) -> bool:
        return await self._delegate.start_camera(camera_identifier)

    async def stop_camera(self, camera_identifier) -> bool:
        return await self._delegate.stop_camera(camera_identifier)

    async def restart_camera(self, camera_identifier) -> bool:
        return await self._delegate.restart_camera(camera_identifier)

    def status(self) -> Dict[int, Dict[str, Any]]:
        return self._delegate.status()

    def list_workers(self) -> List[int]:
        return list(self._delegate._workers.keys())

    def get_worker(self, camera_id: int) -> Any:
        return self._delegate.get_worker(camera_id)

    def health_check(self, camera_id: int | None = None) -> Dict[int, Dict[str, Any]] | Dict[str, Any]:
        # delegate.status provides health per worker; if camera_id provided return single
        s = self._delegate.status()
        if camera_id is None:
            return s
        return s.get(camera_id, {"running": False})

    async def shutdown(self) -> None:
        await self._delegate.stop_all()
