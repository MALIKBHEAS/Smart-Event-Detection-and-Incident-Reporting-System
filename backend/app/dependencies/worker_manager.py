from __future__ import annotations

from typing import cast

from app.workers.protocols import WorkerManagerProtocol
from fastapi import HTTPException, Request


def get_worker_manager(request: Request) -> WorkerManagerProtocol:
    """FastAPI dependency provider that returns the WorkerManager instance from
    the application state.

    Raises HTTPException(503) if the manager is not available.
    """
    manager = getattr(request.app.state, "worker_manager", None) if request is not None else None
    if manager is None:
        raise HTTPException(status_code=503, detail="WorkerManager not initialized")
    return cast(WorkerManagerProtocol, manager)
