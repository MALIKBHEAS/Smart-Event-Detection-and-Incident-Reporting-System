from app.services.event_fusion_service import EventFusionService
from app.services.health_service import HealthService


class DummyWorkerManager:
    def list_workers(self):
        return [1, 2]

    def status(self):
        return {1: {"running": True}, 2: {"running": True}}


class DummyEventFusionService(EventFusionService):
    pass


class DummyDatabaseHealthService:
    def __init__(self, result):
        self._result = result

    def check(self):
        return self._result


def test_health_service_aggregates_subsystems():
    database_health = DummyDatabaseHealthService({"status": "connected", "latency_ms": 5})
    worker_manager = DummyWorkerManager()
    event_fusion = DummyEventFusionService()
    service = HealthService(database_health, worker_manager, event_fusion, version="1.0.0", start_time=1.0)

    health = service.get_health()

    assert health["status"] == "healthy"
    assert health["version"] == "1.0.0"
    assert health["uptime"].endswith("s")
    assert health["services"]["database"]["status"] == "connected"
    assert health["services"]["event_fusion"]["status"] == "running"
    assert health["services"]["worker_manager"]["status"] == "running"
    assert health["workers"]["active"] == 2


def test_health_service_is_ready_and_alive():
    database_health = DummyDatabaseHealthService({"status": "connected", "latency_ms": 1})
    worker_manager = DummyWorkerManager()
    event_fusion = DummyEventFusionService()
    service = HealthService(database_health, worker_manager, event_fusion, version="1.0.0", start_time=1.0)

    assert service.is_ready() is True
    assert service.is_alive() is True


def test_health_service_degraded_when_component_unavailable():
    database_health = DummyDatabaseHealthService({"status": "unavailable", "latency_ms": 1})
    worker_manager = DummyWorkerManager()
    event_fusion = DummyEventFusionService()
    service = HealthService(database_health, worker_manager, event_fusion, version="1.0.0", start_time=1.0)

    assert service.get_health()["status"] == "degraded"
    assert service.is_ready() is False
