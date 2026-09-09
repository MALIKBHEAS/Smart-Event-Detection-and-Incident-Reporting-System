from app.main import app
from fastapi.testclient import TestClient


class DummyWorkerManager:
    async def start_all(self) -> None:
        return None

    async def stop_all(self) -> None:
        return None

    async def start_camera(self, camera_identifier) -> bool:
        return True

    async def stop_camera(self, camera_identifier) -> bool:
        return True

    async def restart_camera(self, camera_identifier) -> bool:
        return True

    def status(self) -> dict:
        return {}

    def list_workers(self) -> list:
        return []

    def health_check(self, camera_id=None) -> dict:
        return {"running": True}


def test_health_endpoint_returns_healthy_status(monkeypatch):
    dummy_manager = DummyWorkerManager()
    monkeypatch.setattr("app.providers.worker_manager_provider.create_worker_manager", lambda settings=None: dummy_manager)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    # Basic expected fields in the upgraded health response
    assert data.get("status") == "healthy"
    assert "version" in data
    assert "uptime" in data and isinstance(data["uptime"], str)
    services = data.get("services", {})
    assert services.get("worker_manager") == {"status": "running"}
    assert services.get("event_fusion") == {"status": "running"}
    # database may be 'not_configured' in test env
    assert services.get("database", {}).get("status") in ("not_configured", "connected", "unavailable")
    assert services.get("database", {}).get("latency_ms") is None or isinstance(services.get("database", {}).get("latency_ms"), int)
    assert data.get("workers", {}).get("active") == 0


def test_workers_health_endpoint_returns_worker_status(monkeypatch):
    class WorkerManagerWithWorkers(DummyWorkerManager):
        def status(self) -> dict:
            return {1: {"running": True}}

        def list_workers(self) -> list:
            return [1]

    dummy_manager = WorkerManagerWithWorkers()
    monkeypatch.setattr("app.providers.worker_manager_provider.create_worker_manager", lambda settings=None: dummy_manager)

    with TestClient(app) as client:
        response = client.get("/health/workers")

    assert response.status_code == 200
    assert response.json()["workers"] == {"1": {"running": True}}
