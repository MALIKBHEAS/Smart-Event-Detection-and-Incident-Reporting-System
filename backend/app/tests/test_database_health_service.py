
from app.services.database_health_service import DatabaseHealthService


class DummyConnection:
    def execute(self, *args, **kwargs):
        return 1


class DummyConnectionCM:
    def __enter__(self):
        return DummyConnection()

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyEngine:
    def connect(self):
        return DummyConnectionCM()


class DummyEngineFail:
    def connect(self):
        raise RuntimeError("cannot connect")


def test_database_health_service_connected():
    service = DatabaseHealthService(engine=DummyEngine(), enabled=True)
    status = service.check()

    assert status["status"] == "connected"
    assert isinstance(status["latency_ms"], int)
    assert status["latency_ms"] >= 0


def test_database_health_service_unavailable_on_connect_error():
    service = DatabaseHealthService(engine=DummyEngineFail(), enabled=True)
    status = service.check()

    assert status["status"] == "unavailable"
    assert isinstance(status["latency_ms"], int)
    assert status["latency_ms"] >= 0


def test_database_health_service_not_configured_when_disabled():
    service = DatabaseHealthService(engine=DummyEngine(), enabled=False)
    status = service.check()

    assert status == {"status": "not_configured", "latency_ms": None}


def test_database_health_service_unavailable_without_engine():
    service = DatabaseHealthService(engine=None, enabled=True)
    status = service.check()

    assert status == {"status": "unavailable", "latency_ms": None}
