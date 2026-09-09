import time
import datetime
from typing import Dict, Any

from app.services.health_monitor.collectors import (
    get_cpu_health,
    get_memory_health,
    get_gpu_health,
    get_storage_health,
    get_network_health,
)
from app.services.health_monitor.registry import HealthRegistry

class HealthAggregator:
    _cached_result: Dict[str, Any] = {}
    _last_update: float = 0.0
    CACHE_DURATION = 3.0

    @classmethod
    def get_components_health(cls) -> Dict[str, Any]:
        now = time.time()
        if now - cls._last_update < cls.CACHE_DURATION and cls._cached_result:
            return cls._cached_result
            
        components = {
            "yolo": HealthRegistry.get_status("yolo"),
            "tracker": HealthRegistry.get_status("tracker"),
            "storage": get_storage_health(),
            "cpu": get_cpu_health(),
            "memory": get_memory_health(),
            "gpu": get_gpu_health(),
            "network": get_network_health(),
        }
        
        cls._cached_result = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "components": components
        }
        cls._last_update = now
        return cls._cached_result
