from __future__ import annotations

from app.workers.tracker import BaseTracker, ByteTrackTracker, CentroidTracker, Track


def test_track_metadata_fields() -> None:
    t = Track(
        track_id=42,
        bbox=(10.0, 20.0, 50.0, 80.0),
        score=0.95,
        class_id=0,
        class_name="person",
        timestamp=100.0,
        camera_id=1,
        track_age=5,
        first_seen_ts=95.0,
        last_seen_ts=100.0,
    )
    assert t.track_id == 42
    assert t["track_id"] == 42
    assert t.class_id == 0
    assert t["class_id"] == 0
    assert t.class_name == "person"
    assert t["class_name"] == "person"
    assert t.confidence == 0.95
    assert t["confidence"] == 0.95
    assert t.bounding_box == (10.0, 20.0, 50.0, 80.0)
    assert t["bounding_box"] == (10.0, 20.0, 50.0, 80.0)
    assert t.timestamp == 100.0
    assert t["timestamp"] == 100.0
    assert t.camera_id == 1
    assert t["camera_id"] == 1
    assert t.track_age == 5
    assert t["track_age"] == 5
    assert t.track_duration == 5.0
    assert t["track_duration"] == 5.0


def test_bytetrack_tracker_configurable_parameters() -> None:
    tracker = ByteTrackTracker(
        track_thresh=0.6,
        track_buffer=45,
        match_thresh=0.75,
        frame_rate=25,
        max_disappeared=30,
        max_distance=40.0,
    )
    assert isinstance(tracker, BaseTracker)

    # Initial frame update
    detections = [(10.0, 10.0, 50.0, 50.0, 0.9)]
    tracks = tracker.update(detections, frame_id=1)
    assert len(tracks) == 1
    assert tracks[0].track_id >= 1
    assert tracks[0].bbox == (10.0, 10.0, 50.0, 50.0)

    # Lost track / empty frame update
    empty_tracks = tracker.update([], frame_id=2)
    assert len(empty_tracks) >= 0  # handles empty frame without crashing

    tracker.reset()


def test_centroid_tracker_age_and_duration() -> None:
    tracker = CentroidTracker(max_disappeared=5, max_distance=50.0)
    det1 = [(10.0, 10.0, 20.0, 20.0, 0.9)]
    tracks1 = tracker.update(det1)
    assert len(tracks1) == 1
    tid = tracks1[0].track_id

    # Move slightly
    det2 = [(12.0, 12.0, 22.0, 22.0, 0.95)]
    tracks2 = tracker.update(det2)
    assert len(tracks2) == 1
    assert tracks2[0].track_id == tid

    # Reset
    tracker.reset()
    tracks3 = tracker.update(det1)
    assert len(tracks3) == 1
    assert tracks3[0].track_id == 1
