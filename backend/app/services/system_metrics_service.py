"""System resource + pipeline metrics for the System Health page.

Additive to the existing /health endpoint (which stays untouched) -- this
provides the richer resource/queue/worker detail the System Health page
needs. Any metric with no real source (GPU, per-camera FPS/latency without
a telemetry pipeline) is reported as unavailable rather than faked.
"""
from __future__ import annotations

import platform
import sys
import time
from typing import Any, Dict, Optional

import psutil

from app.workers.protocols import WorkerManagerProtocol

_PROCESS_START = time.time()


def _gpu_metrics() -> Dict[str, Any]:
    """Best-effort GPU detection via torch, if installed. No fake values --
    if torch/CUDA isn't available (the default install; see
    requirements-yolo.txt), this honestly reports unavailable."""
    try:
        import torch  # noqa: PLC0415 (intentionally optional/lazy)

        if not torch.cuda.is_available():
            return {"available": False, "reason": "No CUDA device detected"}
        device_count = torch.cuda.device_count()
        devices = []
        for i in range(device_count):
            free_bytes, total_bytes = torch.cuda.mem_get_info(i)
            used_pct = round((1 - free_bytes / total_bytes) * 100, 1) if total_bytes else None
            devices.append(
                {
                    "name": torch.cuda.get_device_name(i),
                    "memory_used_pct": used_pct,
                }
            )
        return {"available": True, "devices": devices}
    except Exception:
        return {"available": False, "reason": "torch not installed (see requirements-yolo.txt)"}


class SystemMetricsService:
    def __init__(self, worker_manager: Optional[WorkerManagerProtocol]) -> None:
        self._worker_manager = worker_manager

    def get_metrics(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        workers_detail: Dict[Any, Any] = {}
        if self._worker_manager is not None:
            try:
                workers_detail = self._worker_manager.status()
            except Exception:
                workers_detail = {}

        queue_sizes = [w.get("queue_size") for w in workers_detail.values() if isinstance(w, dict) and w.get("queue_size") is not None]
        connected_count = sum(1 for w in workers_detail.values() if isinstance(w, dict) and w.get("connected"))

        return {
            "cpu": {"percent": cpu_percent, "core_count": psutil.cpu_count() or 0},
            "memory": {
                "percent": memory.percent,
                "used_mb": round(memory.used / (1024 * 1024), 1),
                "total_mb": round(memory.total / (1024 * 1024), 1),
            },
            "disk": {
                "percent": disk.percent,
                "used_gb": round(disk.used / (1024**3), 2),
                "total_gb": round(disk.total / (1024**3), 2),
            },
            "gpu": _gpu_metrics(),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "process_uptime_seconds": round(time.time() - _PROCESS_START, 1),
            "workers": {
                "total": len(workers_detail),
                "connected": connected_count,
            },
            "queue_sizes": queue_sizes,
            # Per-camera processing FPS / detection latency would need a
            # telemetry counter added to the frame-processing loop itself
            # (app/workers/pipeline/frame_processor.py), which doesn't exist
            # yet -- reported as unavailable rather than estimated/faked.
            "processing_fps": None,
            "detection_latency_ms": None,
        }
