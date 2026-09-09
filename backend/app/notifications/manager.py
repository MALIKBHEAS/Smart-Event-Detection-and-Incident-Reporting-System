"""WebSocket connection manager for real-time notifications.

Broadcasts must be callable from the background worker thread (events are
persisted via EventFusionService.ingest(), invoked through
asyncio.to_thread from worker.py -- a real OS thread, not the asyncio event
loop). broadcast_threadsafe() bridges that with run_coroutine_threadsafe
against the loop captured at app startup.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    def broadcast_threadsafe(self, payload: Dict[str, Any]) -> None:
        """Safe to call from any thread (e.g. the worker pipeline)."""
        if self._loop is None or not self._connections:
            return
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)
        except Exception:
            logger.exception("Failed to schedule notification broadcast")

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Process-wide singleton: the worker pipeline and the WebSocket router both
# need to reach the same connection set.
connection_manager = NotificationConnectionManager()
