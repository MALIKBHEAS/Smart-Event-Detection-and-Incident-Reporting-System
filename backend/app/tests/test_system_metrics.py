from __future__ import annotations

from app.services.system_metrics_service import SystemMetricsService


def test_system_metrics_service_returns_real_cpu_memory_disk() -> None:
    service = SystemMetricsService(worker_manager=None)
    metrics = service.get_metrics()

    assert 0.0 <= metrics["cpu"]["percent"] <= 100.0
    assert metrics["cpu"]["core_count"] >= 1
    assert 0.0 <= metrics["memory"]["percent"] <= 100.0
    assert metrics["memory"]["total_mb"] > 0
    assert metrics["disk"]["total_gb"] > 0
    assert metrics["python_version"]
    assert metrics["workers"] == {"total": 0, "connected": 0}
    assert metrics["queue_sizes"] == []
    # Never faked: no telemetry pipeline exists for these yet.
    assert metrics["processing_fps"] is None
    assert metrics["detection_latency_ms"] is None


def test_system_metrics_gpu_honestly_unavailable_without_torch() -> None:
    service = SystemMetricsService(worker_manager=None)
    metrics = service.get_metrics()
    # In this test environment torch/ultralytics aren't installed by
    # default (see requirements-yolo.txt), so GPU must be reported
    # unavailable rather than guessed.
    assert metrics["gpu"]["available"] is False
    assert "reason" in metrics["gpu"]


def test_system_metrics_endpoint_requires_auth() -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        assert client.get("/system/metrics").status_code == 401


def test_system_metrics_endpoint_returns_data_when_authenticated() -> None:
    from app.db.session import SessionLocal
    from app.main import app
    from fastapi.testclient import TestClient
    from sqlalchemy import text

    session = SessionLocal()
    session.execute(text("DELETE FROM user_roles"))
    session.execute(text("DELETE FROM refresh_tokens"))
    session.execute(text("DELETE FROM users"))
    session.commit()
    session.close()

    with TestClient(app) as client:
        client.post("/auth/register", json={"username": "metricsuser", "email": "m@example.com", "password": "supersecret123"})
        login = client.post("/auth/login", json={"username": "metricsuser", "password": "supersecret123"})
        token = login.json()["access_token"]

        resp = client.get("/system/metrics", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert "cpu" in body and "memory" in body and "disk" in body and "gpu" in body

    session = SessionLocal()
    session.execute(text("DELETE FROM user_roles"))
    session.execute(text("DELETE FROM refresh_tokens"))
    session.execute(text("DELETE FROM users"))
    session.commit()
    session.close()
