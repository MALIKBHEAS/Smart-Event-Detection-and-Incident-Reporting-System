import sys
import types

import pytest
from app.workers import tracker as tracker_module
from app.workers.manager import WorkerManager
from app.workers.worker import RTSPDetectionWorker


class DummySession:
    def __init__(self, cameras):
        self._cameras = cameras

    def query(self, model):
        class Q:
            def __init__(self, cams):
                self._cams = cams

            def filter(self, *args, **kwargs):
                return self

            def all(self):
                return self._cams

            def one_or_none(self):
                return None

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


async def _noop_start(self):
    # simple fake start that marks worker as started without opening video capture
    self._started = True


async def _noop_stop(self):
    self._started = False


@pytest.mark.asyncio
async def test_byetrack_selected_when_available(monkeypatch):
    # Prepare dummy ByteTrack backend module
    class DummyBYTE:
        def __init__(self, *a, **kw):
            self._kw = kw

        def update(self, dets, frame_id=None):
            return []

        def reset(self):
            pass

    mod = types.ModuleType('bytetrack')
    mod.BYTETracker = DummyBYTE
    monkeypatch.setitem(sys.modules, 'bytetrack', mod)

    # Prepare fake cameras
    cams = [FakeCamera(1, 'cam1', 'rtsp://fake/1'), FakeCamera(2, 'cam2', 'rtsp://fake/2')]
    session_factory = lambda: DummySession(cams)

    # Ensure RTSPDetectionWorker start/stop are no-op to avoid real capture
    monkeypatch.setattr(RTSPDetectionWorker, 'start', _noop_start)
    monkeypatch.setattr(RTSPDetectionWorker, 'stop', _noop_stop)

    manager = WorkerManager(session_factory=session_factory)

    # start_all should initialize trackers and workers without raising
    await manager.start_all()

    # Verify workers created for each camera
    assert set(manager._workers.keys()) == {1, 2}

    # Verify ByteTrack was initialized for workers (tracker backend present)
    for cam_id, worker in manager._workers.items():
        tr = getattr(worker, '_tracker', None)
        assert tr is not None, 'Tracker should be attached to worker'
        # ByteTrack wrapper sets _backend when backend available
        backend = getattr(tr, '_backend', None)
        assert backend is not None, 'ByteTrack backend should be initialized'
        assert hasattr(tr, 'update') and hasattr(tr, 'reset')

    # stop_all should stop workers
    await manager.stop_all()
    assert manager._workers == {}


@pytest.mark.asyncio
async def test_fallback_selected_when_byetrack_missing(monkeypatch):
    # Ensure no bytetrack module present
    if 'bytetrack' in sys.modules:
        monkeypatch.delitem(sys.modules, 'bytetrack', raising=False)

    # Prepare fake cameras with metadata disabling byte usage per camera
    cams = [FakeCamera(3, 'cam3', 'rtsp://fake/3', metadata={'tracker': {'use_byte': False}}),
            FakeCamera(4, 'cam4', 'rtsp://fake/4')]
    session_factory = lambda: DummySession(cams)

    # Patch RTSPDetectionWorker start/stop to avoid real capture
    monkeypatch.setattr(RTSPDetectionWorker, 'start', _noop_start)
    monkeypatch.setattr(RTSPDetectionWorker, 'stop', _noop_stop)

    manager = WorkerManager(session_factory=session_factory)

    # Start all workers; this should not crash even though ByteTrack is absent
    await manager.start_all()
    assert set(manager._workers.keys()) == {3, 4}

    # Verify trackers implement update/reset and ByteTrack backend is absent
    for cam_id, worker in manager._workers.items():
        tr = getattr(worker, '_tracker', None)
        assert tr is not None
        assert hasattr(tr, 'update') and hasattr(tr, 'reset')
        backend = getattr(tr, '_backend', None)
        # backend should be None for fallback
        assert backend is None

    # Now stop all
    await manager.stop_all()
    assert manager._workers == {}


@pytest.mark.asyncio
async def test_multiple_workers_and_configurable_parameters(monkeypatch):
    # Simulate bytetrack present for one test and absent for another
    class DummyBYTE:
        def __init__(self, *a, **kw):
            self.kw = kw

        def update(self, dets, frame_id=None):
            return []

        def reset(self):
            pass

    mod = types.ModuleType('bytetrack')
    mod.BYTETracker = DummyBYTE
    monkeypatch.setitem(sys.modules, 'bytetrack', mod)

    # Create cameras with per-camera tracker config
    cams = [
        FakeCamera(5, 'cam5', 'rtsp://fake/5', metadata={'tracker': {'use_byte': True, 'max_disappeared': 10}}),
        FakeCamera(6, 'cam6', 'rtsp://fake/6', metadata={'tracker': {'use_byte': False, 'max_distance': 20}}),
    ]
    session_factory = lambda: DummySession(cams)

    monkeypatch.setattr(RTSPDetectionWorker, 'start', _noop_start)
    monkeypatch.setattr(RTSPDetectionWorker, 'stop', _noop_stop)

    manager = WorkerManager(session_factory=session_factory)
    await manager.start_all()

    # Check trackers configured per-camera
    t5 = manager._workers[5]._tracker
    t6 = manager._workers[6]._tracker
    assert getattr(t5, '_backend', None) is not None
    assert getattr(t6, '_backend', None) is None

    # Ensure tracker methods present
    for tr in (t5, t6):
        assert hasattr(tr, 'update') and hasattr(tr, 'reset')

    await manager.stop_all()
    assert manager._workers == {}


def test_metadata_overrides_env(monkeypatch):
    """If camera.metadata contains tracker.use_byte it overrides environment."""
    monkeypatch.setenv('TRACKER_USE_BYTE', 'false')
    # metadata requests use_byte True and specific params
    cam = FakeCamera(10, 'cam10', 'rtsp://fake/10', metadata={'tracker': {'use_byte': True, 'max_disappeared': 30, 'max_distance': 12.5}})

    called = {}

    from app.workers import manager as manager_module

    def fake_create_tracker(use_byte=True, **kwargs):
        # record call
        called['use_byte'] = use_byte
        called['kwargs'] = kwargs
        # return an object that appears to have a _backend (simulates ByteTrack initialized)
        obj = types.SimpleNamespace(_backend=object())
        return obj

    monkeypatch.setattr(manager_module, 'create_tracker', fake_create_tracker)

    wm = WorkerManager(session_factory=lambda: DummySession([cam]))
    tracker_obj = wm._build_tracker_from_config(cam)

    assert called['use_byte'] is True
    assert called['kwargs']['max_disappeared'] == 30
    assert called['kwargs']['max_distance'] == 12.5
    # ensure returned object is the fake tracker
    assert getattr(tracker_obj, '_backend', None) is not None


@pytest.mark.asyncio
async def test_caplog_byetrack_init_logs(monkeypatch, caplog):
    """When ByteTrack is available, WorkerManager logs initialization (caplog)."""
    class DummyBYTE:
        def __init__(self, *a, **kw):
            self._kw = kw
        def update(self, dets, frame_id=None):
            return []
        def reset(self):
            pass
    mod = types.ModuleType('bytetrack')
    mod.BYTETracker = DummyBYTE
    monkeypatch.setitem(sys.modules, 'bytetrack', mod)

    cams = [FakeCamera(21, 'cam21', 'rtsp://fake/21')]
    session_factory = lambda: DummySession(cams)
    monkeypatch.setattr(RTSPDetectionWorker, 'start', _noop_start)
    monkeypatch.setattr(RTSPDetectionWorker, 'stop', _noop_stop)

    manager = WorkerManager(session_factory=session_factory)
    caplog.set_level('INFO')
    await manager.start_all()

    messages = [r.getMessage() for r in caplog.records]
    assert any('ByteTrack initialized' in m for m in messages), f"Expected ByteTrack initialized log; got: {messages}"
    tr = manager._workers[21]._tracker
    assert getattr(tr, '_backend', None) is not None
    await manager.stop_all()


@pytest.mark.asyncio
async def test_caplog_fallback_logs_when_missing(monkeypatch, caplog):
    """When ByteTrack is missing, WorkerManager logs fallback usage (caplog)."""
    if 'bytetrack' in sys.modules:
        monkeypatch.delitem(sys.modules, 'bytetrack', raising=False)

    cams = [FakeCamera(22, 'cam22', 'rtsp://fake/22')]
    session_factory = lambda: DummySession(cams)
    monkeypatch.setattr(RTSPDetectionWorker, 'start', _noop_start)
    monkeypatch.setattr(RTSPDetectionWorker, 'stop', _noop_stop)

    manager = WorkerManager(session_factory=session_factory)
    caplog.set_level('INFO')
    await manager.start_all()

    messages = [r.getMessage() for r in caplog.records]
    assert any('using fallback tracker' in m or 'ByteTrack not found' in m for m in messages), f"Expected fallback log; got: {messages}"
    tr = manager._workers[22]._tracker
    assert getattr(tr, '_backend', None) is None
    await manager.stop_all()


@pytest.mark.asyncio
async def test_caplog_tracker_init_failure_logs_and_fallback(monkeypatch, caplog):
    """If tracker creation raises, WorkerManager logs an error and falls back."""
    # Ensure bytetrack absent
    if 'bytetrack' in sys.modules:
        monkeypatch.delitem(sys.modules, 'bytetrack', raising=False)

    orig_create = tracker_module.create_tracker

    def side_effect_create(use_byte=True, **kwargs):
        if not hasattr(side_effect_create, 'called'):
            side_effect_create.called = True
            raise RuntimeError('simulated init error')
        # delegate to original but force fallback
        return orig_create(use_byte=False, **kwargs)

    from app.workers import manager as manager_module

    monkeypatch.setattr(manager_module, 'create_tracker', side_effect_create)

    cams = [FakeCamera(23, 'cam23', 'rtsp://fake/23')]
    session_factory = lambda: DummySession(cams)
    monkeypatch.setattr(RTSPDetectionWorker, 'start', _noop_start)
    monkeypatch.setattr(RTSPDetectionWorker, 'stop', _noop_stop)

    manager = WorkerManager(session_factory=session_factory)
    caplog.set_level('ERROR')
    await manager.start_all()

    error_msgs = [r.getMessage() for r in caplog.records if r.levelname == 'ERROR' or r.levelname == 'CRITICAL']
    assert any('Failed to create tracker' in m or 'simulated init error' in m for m in error_msgs), f"Expected error log about tracker init; got: {error_msgs}"

    tr = manager._workers[23]._tracker
    assert getattr(tr, '_backend', None) is None

    await manager.stop_all()
    # restore
    monkeypatch.setattr(manager_module, 'create_tracker', orig_create)


def test_env_used_when_no_metadata(monkeypatch):
    """If no camera metadata present, environment variables are used."""
    monkeypatch.setenv('TRACKER_USE_BYTE', 'false')
    monkeypatch.setenv('TRACKER_MAX_DISAPPEARED', '7')
    monkeypatch.setenv('TRACKER_MAX_DISTANCE', '9.5')

    cam = FakeCamera(11, 'cam11', 'rtsp://fake/11', metadata=None)

    called = {}

    from app.workers import manager as manager_module

    def fake_create_tracker(use_byte=True, **kwargs):
        called['use_byte'] = use_byte
        called['kwargs'] = kwargs
        return types.SimpleNamespace(_backend=None)

    monkeypatch.setattr(manager_module, 'create_tracker', fake_create_tracker)

    wm = WorkerManager(session_factory=lambda: DummySession([cam]))
    wm._build_tracker_from_config(cam)

    assert called['use_byte'] is False
    assert called['kwargs']['max_disappeared'] == 7
    assert called['kwargs']['max_distance'] == 9.5


def test_invalid_metadata_values_fallback_to_defaults(monkeypatch):
    """Invalid numeric metadata should be ignored and defaults used."""
    cam = FakeCamera(12, 'cam12', 'rtsp://fake/12', metadata={'tracker': {'use_byte': True, 'max_disappeared': 'notint', 'max_distance': 'notfloat'}})

    called = {}

    from app.workers import manager as manager_module

    def fake_create_tracker(use_byte=True, **kwargs):
        called['use_byte'] = use_byte
        called['kwargs'] = kwargs
        return types.SimpleNamespace(_backend=None)

    monkeypatch.setattr(manager_module, 'create_tracker', fake_create_tracker)

    wm = WorkerManager(session_factory=lambda: DummySession([cam]))
    wm._build_tracker_from_config(cam)

    assert called['use_byte'] is True
    # defaults from manager are 50 and 50.0
    assert called['kwargs']['max_disappeared'] == 50
    assert called['kwargs']['max_distance'] == 50.0


def test_create_tracker_exception_triggers_fallback(monkeypatch):
    """If create_tracker raises, manager should call create_tracker with use_byte=False as fallback."""
    cam = FakeCamera(13, 'cam13', 'rtsp://fake/13', metadata={'tracker': {'use_byte': True}})

    calls = []

    from app.workers import manager as manager_module

    def fake_create_tracker(use_byte=True, **kwargs):
        calls.append(use_byte)
        if use_byte:
            raise RuntimeError('backend init failed')
        return types.SimpleNamespace(_backend=None)

    monkeypatch.setattr(manager_module, 'create_tracker', fake_create_tracker)

    wm = WorkerManager(session_factory=lambda: DummySession([cam]))
    tracker_obj = wm._build_tracker_from_config(cam)

    # first call attempted with True and raised, second call used False
    assert calls[0] is True
    assert calls[1] is False
    assert getattr(tracker_obj, '_backend', None) is None
