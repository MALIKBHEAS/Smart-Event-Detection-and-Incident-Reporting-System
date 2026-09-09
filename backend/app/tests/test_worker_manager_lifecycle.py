import asyncio
import time
import types
from typing import List

import app.workers.manager as manager_module
import pytest
from app.workers.manager import WorkerManager


class DummySession:
    def __init__(self, cameras: List[object]):
        self._cameras = cameras

    def query(self, model):
        class Q:
            def __init__(self, cams):
                self._cams = cams

            def filter(self, *args, **kwargs):
                filtered = self._cams
                for arg in args:
                    try:
                        col_name = arg.left.name
                        val = arg.right.value
                        filtered = [c for c in filtered if getattr(c, col_name, None) == val]
                    except Exception:
                        pass
                return Q(filtered)

            def all(self):
                return self._cams

            def one_or_none(self):
                # return first camera if present
                return self._cams[0] if self._cams else None

        return Q(self._cameras)

    def close(self):
        pass


class FakeCamera:
    def __init__(self, id, name, rtsp_url, metadata=None, is_active=True):
        self.id = id
        self.name = name
        self.rtsp_url = rtsp_url
        self.metadata = metadata
        self.is_active = is_active


class FakeWorker:
    """A lightweight fake RTSPDetectionWorker replacement used for tests.

    It mimics the minimal async lifecycle and health_check interface expected by
    WorkerManager without touching OpenCV, detectors, or trackers.
    """

    instances: List[object] = []

    def __init__(self, config, tracker=None):
        # store config for assertions
        self.config = config
        self._tracker = tracker
        self._started = False
        self._released = False
        self._last_activity = None
        self._error = None
        # record instance for external checks
        FakeWorker.instances.append(self)

    async def start(self):
        # simulate small startup delay
        await asyncio.sleep(0)
        if getattr(self, "_should_fail_on_start", False):
            raise RuntimeError("simulated startup failure")
        self._started = True
        self._last_activity = time.time()

    async def stop(self):
        self._started = False
        # simulate resource release
        self._released = True
        await asyncio.sleep(0)

    async def restart(self):
        await self.stop()
        await self.start()

    def health_check(self):
        return {
            "camera_name": getattr(self.config, "camera_name", None),
            "running": bool(self._started),
            "tracker_status": getattr(self._tracker, "_backend", None) is not None if self._tracker is not None else False,
            "last_activity": self._last_activity,
            "error": self._error,
        }


@pytest.mark.asyncio
async def test_start_camera(monkeypatch):
    """Start Camera: verify WorkerManager starts worker and registers it."""
    cams = [FakeCamera(101, "cam101", "rtsp://fake/101")]

    session_factory = lambda: DummySession(cams)

    # patch the worker class used by the manager
    monkeypatch.setattr(manager_module, "RTSPDetectionWorker", FakeWorker)
    # ensure tracker creation returns a simple object (no backend)
    monkeypatch.setattr(manager_module, "create_tracker", lambda **kw: types.SimpleNamespace(_backend=None))

    wm = WorkerManager(session_factory=session_factory)

    started = await wm.start_camera(101)
    assert started is True, "start_camera should return True on successful start"
    assert 101 in wm._workers

    w = wm._workers[101]
    assert w._started is True
    assert w.config.event_detectors == []

    # status should reflect running worker
    st = wm.status()
    assert 101 in st
    assert st[101]["running"] is True
    assert st[101]["camera_name"] == getattr(w.config, "camera_name", None)

    # cleanup
    await wm.stop_all()


@pytest.mark.asyncio
async def test_start_camera_with_event_detector_config(monkeypatch):
    cams = [FakeCamera(107, "cam107", "rtsp://fake/107")]
    session_factory = lambda: DummySession(cams)

    monkeypatch.setattr(manager_module, "RTSPDetectionWorker", FakeWorker)
    monkeypatch.setattr(manager_module, "create_tracker", lambda **kw: types.SimpleNamespace(_backend=None))

    # Attach an event detector configuration onto the camera record
    cams[0].detector_config = {
        "event_detectors": [
            {"name": "restricted_area", "areas": {"zone1": [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]}}
        ]
    }

    wm = WorkerManager(session_factory=session_factory)
    started = await wm.start_camera(107)

    assert started is True
    assert 107 in wm._workers
    assert wm._workers[107].config.event_detectors == cams[0].detector_config["event_detectors"]

    await wm.stop_all()


@pytest.mark.asyncio
async def test_stop_camera(monkeypatch):
    """Stop Camera: ensure stop_camera stops the correct worker and releases resources."""
    cams = [FakeCamera(102, "cam102", "rtsp://fake/102")]
    session_factory = lambda: DummySession(cams)

    monkeypatch.setattr(manager_module, "RTSPDetectionWorker", FakeWorker)
    monkeypatch.setattr(manager_module, "create_tracker", lambda **kw: types.SimpleNamespace(_backend=None))

    wm = WorkerManager(session_factory=session_factory)
    await wm.start_camera(102)
    assert 102 in wm._workers

    stopped = await wm.stop_camera(102)
    assert stopped is True
    assert 102 not in wm._workers

    # verify resource released on the worker instance
    assert any(getattr(inst, "_released", False) for inst in FakeWorker.instances), "Worker should have been released"


@pytest.mark.asyncio
async def test_restart_camera(monkeypatch):
    """Restart Camera: stopped worker can be restarted and old state is cleaned."""
    cams = [FakeCamera(103, "cam103", "rtsp://fake/103")]
    session_factory = lambda: DummySession(cams)

    # reset instances
    FakeWorker.instances.clear()

    monkeypatch.setattr(manager_module, "RTSPDetectionWorker", FakeWorker)
    monkeypatch.setattr(manager_module, "create_tracker", lambda **kw: types.SimpleNamespace(_backend=None))

    wm = WorkerManager(session_factory=session_factory)
    ok = await wm.start_camera(103)
    assert ok
    first_worker = wm._workers[103]

    # stop
    ok2 = await wm.stop_camera(103)
    assert ok2
    assert 103 not in wm._workers

    # start again
    ok3 = await wm.start_camera(103)
    assert ok3
    assert 103 in wm._workers
    second_worker = wm._workers[103]

    # ensure a distinct worker instance was created and old instance was released
    assert first_worker is not second_worker
    assert getattr(first_worker, "_released", False) is True

    await wm.stop_all()


@pytest.mark.asyncio
async def test_multiple_cameras_independent(monkeypatch):
    """Multiple Cameras: starting/stopping one camera should not affect others."""
    cams = [
        FakeCamera(201, "cam201", "rtsp://fake/201"),
        FakeCamera(202, "cam202", "rtsp://fake/202"),
    ]
    session_factory = lambda: DummySession(cams)

    monkeypatch.setattr(manager_module, "RTSPDetectionWorker", FakeWorker)
    monkeypatch.setattr(manager_module, "create_tracker", lambda **kw: types.SimpleNamespace(_backend=None))

    wm = WorkerManager(session_factory=session_factory)
    await wm.start_camera(201)
    await wm.start_camera(202)

    assert 201 in wm._workers and 202 in wm._workers

    # stop camera 201 only
    await wm.stop_camera(201)
    assert 201 not in wm._workers
    assert 202 in wm._workers

    # ensure remaining worker still running
    assert wm._workers[202]._started is True

    await wm.stop_all()


@pytest.mark.asyncio
async def test_status_reporting_includes_expected_fields(monkeypatch):
    """Status Reporting: returned info includes camera id, worker state, tracker status, last activity, and error."""
    cams = [FakeCamera(301, "cam301", "rtsp://fake/301")]
    session_factory = lambda: DummySession(cams)

    # tracker with backend
    monkeypatch.setattr(manager_module, "create_tracker", lambda **kw: types.SimpleNamespace(_backend="ok"))
    monkeypatch.setattr(manager_module, "RTSPDetectionWorker", FakeWorker)

    wm = WorkerManager(session_factory=session_factory)
    await wm.start_camera(301)

    st = wm.status()
    assert 301 in st

    info = st[301]
    # expected keys
    assert "camera_name" in info
    assert "running" in info
    assert "tracker_status" in info
    assert "last_activity" in info
    assert "error" in info

    # tracker_status should reflect the create_tracker return
    assert info["tracker_status"] is True

    await wm.stop_all()


@pytest.mark.asyncio
async def test_error_handling_on_startup_failure(monkeypatch, caplog):
    """Simulate worker startup failure: verify manager handles it gracefully and logs error."""
    cams = [FakeCamera(401, "cam401", "rtsp://fake/401")]
    session_factory = lambda: DummySession(cams)

    # make the FakeWorker raise on start
    def failing_worker_ctor(config, tracker=None):
        w = FakeWorker(config, tracker)
        w._should_fail_on_start = True
        return w

    monkeypatch.setattr(manager_module, "RTSPDetectionWorker", failing_worker_ctor)
    monkeypatch.setattr(manager_module, "create_tracker", lambda **kw: types.SimpleNamespace(_backend=None))

    wm = WorkerManager(session_factory=session_factory)

    caplog.set_level("ERROR")
    ok = await wm.start_camera(401)
    # should return False because worker.start raised
    assert ok is False

    # manager should not have a worker registered for this camera
    assert 401 not in wm._workers

    # ensure error logged
    assert any("Failed to start worker" in rec.getMessage() or "Exception" in rec.getMessage() for rec in caplog.records)
