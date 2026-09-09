"""Database health utilities."""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


class DatabaseHealthService:
    """Check database readiness and connectivity."""

    def __init__(self, engine: Any | None = None, enabled: bool = True) -> None:
        self.engine = engine
        self.enabled = enabled

    def check(self) -> dict[str, Any]:
        """Return the current database health status.

        Returns a dictionary with at least:
            - status: connected|unavailable|not_configured
            - latency_ms: integer latency in milliseconds or None
        """
        if not self.enabled:
            return {"status": "not_configured", "latency_ms": None}

        if self.engine is None:
            return {"status": "unavailable", "latency_ms": None}

        start = time.perf_counter()
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {"status": "connected", "latency_ms": latency_ms}
        except Exception as exc:
            logger.debug("Database connectivity check failed: %s", exc)
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {"status": "unavailable", "latency_ms": latency_ms}
