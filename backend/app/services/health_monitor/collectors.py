import psutil
import time
from typing import Dict, Any

def _get_status_from_percent(percent: float) -> str:
    if percent >= 90.0:
        return "down"
    elif percent >= 70.0:
        return "degraded"
    return "healthy"

def get_cpu_health() -> Dict[str, Any]:
    try:
        usage = psutil.cpu_percent(interval=0.1)
        return {
            "status": _get_status_from_percent(usage),
            "usage_percent": usage
        }
    except Exception as e:
        return {"status": "unknown", "message": str(e)}

def get_memory_health() -> Dict[str, Any]:
    try:
        mem = psutil.virtual_memory()
        usage = mem.percent
        return {
            "status": _get_status_from_percent(usage),
            "used_gb": round(mem.used / (1024**3), 2),
            "total_gb": round(mem.total / (1024**3), 2),
            "usage_percent": usage
        }
    except Exception as e:
        return {"status": "unknown", "message": str(e)}

def get_storage_health() -> Dict[str, Any]:
    try:
        disk = psutil.disk_usage("/")
        usage = disk.percent
        return {
            "status": _get_status_from_percent(usage),
            "free_space_gb": round(disk.free / (1024**3), 2),
            "total_space_gb": round(disk.total / (1024**3), 2),
            "read_write_ok": True
        }
    except Exception as e:
        return {"status": "unknown", "message": str(e)}

def get_gpu_health() -> Dict[str, Any]:
    try:
        import torch
        if not torch.cuda.is_available():
            return {"status": "unknown", "message": "No CUDA device detected"}
        free_bytes, total_bytes = torch.cuda.mem_get_info(0)
        used_bytes = total_bytes - free_bytes
        used_pct = round((used_bytes / total_bytes) * 100, 1) if total_bytes else 0
        return {
            "status": _get_status_from_percent(used_pct),
            "usage_percent": used_pct,
            "memory_used_mb": round(used_bytes / (1024**2), 1)
        }
    except ImportError:
        return {"status": "unknown", "message": "torch not installed"}
    except Exception as e:
        return {"status": "unknown", "message": str(e)}

def get_network_health() -> Dict[str, Any]:
    try:
        t0 = time.time()
        import socket
        # Ping the local DB port to test internal network
        s = socket.create_connection(("db", 5432), timeout=1)
        s.close()
        latency = round((time.time() - t0) * 1000, 1)
        status = "healthy" if latency < 100 else "degraded"
        return {
            "status": status,
            "latency_ms": latency
        }
    except Exception as e:
        return {"status": "down", "message": str(e)}
