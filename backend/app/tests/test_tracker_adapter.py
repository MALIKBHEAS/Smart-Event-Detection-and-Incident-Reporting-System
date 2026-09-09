import importlib
import sys
import types

from app.workers import tracker


class DummyBackend:
    def __init__(self, *args, **kwargs):
        self._id = 1

    def update(self, dets, frame_id=None):
        # Return format: list of [id, x1, y1, x2, y2, score]
        out = []
        for i, row in enumerate(dets):
            # create a fake track id equals i+1
            out.append([i + 1, float(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4])])
        return out


def test_byetrack_adapter_with_mocked_backend(monkeypatch):
    # Create a fake module and class
    mod = types.ModuleType('bytetrack')
    mod.BYTETracker = DummyBackend
    # Insert into sys.modules
    monkeypatch.setitem(sys.modules, 'bytetrack', mod)
    # Reload tracker module to pick up the fake backend
    importlib.reload(tracker)

    # Create adapter - should find the mocked backend
    adapter = tracker.ByteTrackWrapper()
    # Prepare detections: x1,y1,x2,y2,score
    dets = [(10, 10, 50, 50, 0.9), (100, 100, 150, 150, 0.8)]
    res = adapter.update(dets, frame_id=1)
    assert isinstance(res, list)
    assert len(res) == 2
    assert res[0]['id'] == 1
    assert 'bbox' in res[0]


def test_create_tracker_factory_prefers_byte_with_mock(monkeypatch):
    mod = types.ModuleType('bytetrack')
    mod.BYTETracker = DummyBackend
    monkeypatch.setitem(sys.modules, 'bytetrack', mod)
    importlib.reload(tracker)
    t = tracker.create_tracker(use_byte=True)
    assert hasattr(t, 'update')


def test_centroid_tracker_basic():
    ct = tracker.CentroidTracker(max_disappeared=2, max_distance=100)
    dets = [(10, 10, 50, 50, 0.9)]
    out = ct.update(dets)
    assert len(out) == 1
    assert 'id' in out[0]

