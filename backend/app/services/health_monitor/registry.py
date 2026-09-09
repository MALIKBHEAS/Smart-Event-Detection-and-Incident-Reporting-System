import time
from typing import Dict, Any

class HealthRegistry:
    """In-memory registry to store heartbeats for inference components (YOLO, Tracker)."""
    
    _heartbeats: Dict[str, Dict[str, Any]] = {}
    TIMEOUT_SECONDS = 30.0

    @classmethod
    def record_heartbeat(cls, component_name: str, **kwargs) -> None:
        """Record a heartbeat with optional metrics (e.g. fps, latency_ms)."""
        if component_name not in cls._heartbeats:
            cls._heartbeats[component_name] = {}
        
        cls._heartbeats[component_name]["last_inference_time"] = time.time()
        for k, v in kwargs.items():
            cls._heartbeats[component_name][k] = v

    @classmethod
    def get_status(cls, component_name: str) -> Dict[str, Any]:
        data = cls._heartbeats.get(component_name)
        if not data:
            return {"status": "unknown"}
        
        last_time = data.get("last_inference_time", 0)
        age = time.time() - last_time
        
        if age > cls.TIMEOUT_SECONDS:
            status = "down"
        else:
            status = "healthy"
            
        import datetime
        dt = datetime.datetime.utcfromtimestamp(last_time).isoformat() + "Z"
        
        result = {"status": status, "last_inference_time": dt}
        for k, v in data.items():
            if k != "last_inference_time":
                result[k] = v
                
        return result
