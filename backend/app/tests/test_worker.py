import asyncio

import cv2
import numpy as np
import pytest
from app.workers.detectors import LineCrossingDetector, RestrictedAreaDetector
from app.workers.tracker import CentroidTracker, Track
from app.workers.worker import RTSPDetectionWorker, WorkerConfig


def test_centroid_tracker_basic_matching():
    tracker = CentroidTracker(max_distance=50.0)

    dets1 = [{'bbox': [10, 10, 20, 20]}, {'bbox': [100, 100, 110, 110]}]
    tracks1 = tracker.update(dets1)
    ids1 = sorted([t.track_id for t in tracks1])
    assert ids1 == [1, 2]

    # Move both detections slightly within max_distance so they should match existing IDs
    dets2 = [{'bbox': [12, 12, 22, 22]}, {'bbox': [102, 102, 112, 112]}]
    tracks2 = tracker.update(dets2)
    id_bbox = {t.track_id: t.bbox for t in tracks2}

    # both original IDs should still be present and bboxes updated
    assert 1 in id_bbox and 2 in id_bbox
    assert id_bbox[1] == (12, 12, 22, 22)
    assert id_bbox[2] == (102, 102, 112, 112)


def test_restricted_area_detector_with_synthetic_tracks():
    # area is a 0..50 square
    area = {'id': 'a1', 'name': 'test-area', 'polygon': [(0, 0), (0, 50), (50, 50), (50, 0)]}
    det = RestrictedAreaDetector({'areas': [area]})

    # track 1 inside area, track 2 outside
    t1 = Track(1, (10, 10, 20, 20))
    t2 = Track(2, (60, 60, 70, 70))
    events = det.update(detections=[], tracks=[t1, t2], frame=None, timestamp=123.0)

    assert len(events) == 1
    ev = events[0]
    assert ev['type'] == 'restricted_area_intrusion'
    assert ev['payload']['area_id'] == 'a1'
    assert ev['payload']['track_id'] == 1


def test_line_crossing_detector_with_synthetic_tracks():
    # horizontal line across y=25 from x=0..100
    line = {'id': 'l1', 'p1': (0, 25), 'p2': (100, 25), 'direction': 'both'}
    det = LineCrossingDetector({'lines': [line]})

    # first frame: centroid above the line -> no event but stored as previous
    t_prev = Track(1, (10, 10, 20, 20))  # centroid (15,15)
    ev1 = det.update(detections=[], tracks=[t_prev], frame=None, timestamp=1.0)
    assert ev1 == []

    # second frame: centroid below the line -> crossing should be detected
    t_now = Track(1, (10, 40, 20, 50))  # centroid (15,45)
    ev2 = det.update(detections=[], tracks=[t_now], frame=None, timestamp=2.0)
    assert len(ev2) == 1
    ev = ev2[0]
    assert ev['type'] == 'line_crossing'
    assert ev['payload']['track_id'] == 1


class DummyCapture:
    """Simple fake cv2.VideoCapture-like object that yields a few frames then stops."""

    def __init__(self, frames=3, shape=(24, 24, 3)):
        self._frames_left = frames
        self._shape = shape
        self._released = False

    def isOpened(self):
        return not self._released

    def read(self):
        if self._frames_left <= 0:
            return False, None
        self._frames_left -= 1
        frame = np.zeros(self._shape, dtype=np.uint8)
        return True, frame

    def release(self):
        self._released = True


@pytest.mark.asyncio
async def test_worker_health_and_start_stop(monkeypatch, tmp_path):
    # Prepare config with a dummy source and small timings
    cfg = WorkerConfig(source='dummy', camera_id=1, camera_name='testcam', fps=5, reconnect_interval=0.05)

    # Monkeypatch YOLODetector used by worker to avoid heavy inference
    class FakeYOLO:
        def __init__(self, model_path=None, device='cpu'):
            pass

        def run(self, frame):
            # return empty detections (fast)
            return {'yolo': []}

    monkeypatch.setattr('backend.app.workers.worker.YOLODetector', FakeYOLO)

    # Monkeypatch RTSPDetectionWorker._open_capture to return our DummyCapture
    async def fake_open_capture(self):
        return DummyCapture(frames=2)

    monkeypatch.setattr(RTSPDetectionWorker, '_open_capture', fake_open_capture)

    # Prevent file IO and external systems: no-op save_frame_as_jpeg and EventFusionService.ingest
    monkeypatch.setattr('backend.app.workers.worker.save_frame_as_jpeg', lambda frame, path: None)
    monkeypatch.setattr('backend.app.workers.worker.EventFusionService.ingest', lambda self, t, payload: None)

    # Create the worker and run start/stop
    worker = RTSPDetectionWorker(cfg)
    # health before start
    h = worker.health_check()
    assert h['running'] in (False, None)

    await worker.start()
    # give the worker a short time to run through a couple frames
    await asyncio.sleep(0.15)
    # stop the worker gracefully
    await worker.stop()

    h2 = worker.health_check()
    assert h2['running'] is False


# If cv2.VideoCapture('0') is used by someone, ensure it can be patched to avoid real camera access
def test_cv2_videocapture_monkeypatch(monkeypatch):
    # Replace cv2.VideoCapture to return DummyCapture when '0' is used
    orig_vc = cv2.VideoCapture

    def fake_vc(src):
        if str(src) == '0':
            return DummyCapture(frames=1)
        return orig_vc(src)

    monkeypatch.setattr(cv2, 'VideoCapture', fake_vc)

    cap = cv2.VideoCapture('0')
    ok, frame = cap.read()
    assert ok is True
    assert frame is not None
    cap.release()

    # restore done by pytest monkeypatch teardown
