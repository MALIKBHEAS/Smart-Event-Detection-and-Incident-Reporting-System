
from app.dependencies.worker_manager import get_worker_manager
from app.workers.manager import WorkerManager
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient


def test_dependency_returns_active_manager_instance():
    app = FastAPI()

    # attach a real WorkerManager instance to app.state
    manager = WorkerManager(session_factory=lambda: None)  # session factory not used in this test
    app.state.worker_manager = manager

    @app.get("/test")
    def handler(mgr: WorkerManager = Depends(get_worker_manager)):
        return {"id": id(mgr)}

    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.json()["id"] == id(manager)


def test_multiple_routes_receive_same_instance():
    app = FastAPI()
    manager = WorkerManager(session_factory=lambda: None)
    app.state.worker_manager = manager

    @app.get("/a")
    def a(mgr: WorkerManager = Depends(get_worker_manager)):
        return {"id": id(mgr)}

    @app.get("/b")
    def b(mgr: WorkerManager = Depends(get_worker_manager)):
        return {"id": id(mgr)}

    with TestClient(app) as client:
        ra = client.get("/a")
        rb = client.get("/b")
        assert ra.status_code == 200 and rb.status_code == 200
        assert ra.json()["id"] == rb.json()["id"] == id(manager)


def test_missing_application_state_handled_correctly():
    app = FastAPI()

    @app.get("/test")
    def handler(mgr: WorkerManager = Depends(get_worker_manager)):
        return {"ok": True}

    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "WorkerManager not initialized"


def test_mock_worker_manager_can_be_injected(monkeypatch):
    app = FastAPI()

    class DummyManager:
        def __init__(self):
            self.marker = "dummy"

    # override dependency using FastAPI dependency_overrides
    def override_get_worker_manager(request: Request) -> DummyManager:
        return DummyManager()

    app.dependency_overrides[get_worker_manager] = override_get_worker_manager

    @app.get("/test")
    def handler(mgr=Depends(get_worker_manager)):
        return {"marker": getattr(mgr, "marker", None)}

    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.json()["marker"] == "dummy"
