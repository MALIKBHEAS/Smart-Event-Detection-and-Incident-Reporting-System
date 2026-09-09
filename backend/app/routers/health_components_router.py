from fastapi import APIRouter
from app.services.health_monitor.aggregator import HealthAggregator

router = APIRouter(prefix="/health/components", tags=["health"])

@router.get("")
async def get_health_components():
    """
    Get real-time health status of individual backend components.
    Includes YOLO, Tracker, CPU, Memory, GPU, Storage, and Network.
    """
    return HealthAggregator.get_components_health()
