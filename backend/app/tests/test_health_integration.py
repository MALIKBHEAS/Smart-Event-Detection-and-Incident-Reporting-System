from app.main import app
from app.settings import AppSettings
from fastapi.testclient import TestClient


def test_lifespan_and_health_endpoint():
    # Use TestClient as context manager to trigger startup/shutdown
    with TestClient(app) as client:
        # After startup, application state should contain settings, worker_manager, event_service, start_time
        assert hasattr(app.state, 'settings')
        settings = app.state.settings
        assert isinstance(settings, AppSettings)
        assert hasattr(app.state, 'worker_manager')
        assert hasattr(app.state, 'event_service')
        assert hasattr(app.state, 'start_time')
        assert hasattr(app.state, 'version')

        # Call health endpoint
        resp = client.get('/health')
        assert resp.status_code == 200
        data = resp.json()

        # Basic structure
        assert 'status' in data
        assert 'version' in data
        assert 'uptime' in data
        assert 'services' in data
        assert 'workers' in data

        # version matches settings
        assert data['version'] == getattr(settings, 'version', '1.0.0')

        # uptime should be a string like "0.12s"
        assert isinstance(data['uptime'], str) and data['uptime'].endswith('s')

        # services keys
        services = data['services']
        assert 'worker_manager' in services
        assert 'event_fusion' in services
        assert 'database' in services

        # database service should report at least a status and a latency value
        assert isinstance(services['database'], dict)
        assert services['database']['status'] in ('not_configured', 'connected', 'unavailable')
        assert 'latency_ms' in services['database']
        assert services['database']['latency_ms'] is None or isinstance(services['database']['latency_ms'], int)

        # workers.active present
        assert isinstance(data['workers'], dict)
        assert 'active' in data['workers']
        assert isinstance(data['workers']['active'], int)

    # After context manager exit, the lifespan cleanup should execute and the app should be shut down
    # There's no direct flag to assert here, but absence of exceptions suffices for lifecycle verification
