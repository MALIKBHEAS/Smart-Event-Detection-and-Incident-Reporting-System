from importlib import reload

import pytest


def test_production_returns_real(monkeypatch):
    monkeypatch.setenv('WORKER_MANAGER_TYPE', 'real')
    # reload settings/provider to pick up env
    from app.providers import worker_manager_provider as provider
    reload(provider)
    from app.providers.worker_manager_provider import create_worker_manager
    from app.workers.protocols import WorkerManagerProtocol

    wm = create_worker_manager()
    assert isinstance(wm, WorkerManagerProtocol)


def test_test_returns_mock(monkeypatch):
    monkeypatch.setenv('WORKER_MANAGER_TYPE', 'mock')
    from importlib import reload

    from app.providers import worker_manager_provider as provider
    reload(provider)
    from app.providers.worker_manager_provider import create_worker_manager
    from app.workers.protocols import WorkerManagerProtocol

    wm = create_worker_manager()
    assert isinstance(wm, WorkerManagerProtocol)


def test_invalid_raises(monkeypatch):
    monkeypatch.setenv('WORKER_MANAGER_TYPE', 'unsupported_value')
    from importlib import reload

    from app.providers import worker_manager_provider as provider
    reload(provider)
    from app.providers.worker_manager_provider import create_worker_manager

    with pytest.raises(ValueError):
        create_worker_manager()


def test_fastapi_dependency_receives_selected_impl(monkeypatch):
    # set to mock and ensure the FastAPI app uses provider-produced manager in lifespan
    monkeypatch.setenv('WORKER_MANAGER_TYPE', 'mock')
    from importlib import reload

    from app.providers import worker_manager_provider as provider
    reload(provider)
    from app.dependencies.worker_manager import get_worker_manager
    from app.providers.worker_manager_provider import create_worker_manager
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    # lifespan that uses factory
    @app.on_event('startup')
    async def startup():
        app.state.worker_manager = create_worker_manager()

    @app.on_event('shutdown')
    async def shutdown():
        mgr = getattr(app.state, 'worker_manager', None)
        if mgr is not None:
            await mgr.stop_all()

    @app.get('/who')
    def who(mgr = Depends(get_worker_manager)):
        return {'type': type(mgr).__name__}

    with TestClient(app) as client:
        r = client.get('/who')
        assert r.status_code == 200
        assert r.json()['type'] == 'MockWorkerManager'
