from app.services.event_detector_service import EventDetectorService
from app.workers.detectors import Detection as DetectorDetection
from app.workers.detectors import Track as DetectorTrack


def test_event_detector_service_no_config_creates_empty_detector_list() -> None:
    service = EventDetectorService(None)
    assert not service.has_detectors
    assert service.detect([], []) == []


def test_event_detector_service_skips_unknown_detector() -> None:
    service = EventDetectorService([{"name": "unknown_detector"}])
    assert not service.has_detectors
    assert service.detect([], []) == []


def test_event_detector_service_restricted_area_detects_inside_area() -> None:
    config = [
        {
            "name": "restricted_area",
            "areas": {
                "parking": [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
            },
        }
    ]
    service = EventDetectorService(config)
    assert service.has_detectors

    detection = DetectorDetection(
        id="1",
        label="person",
        bbox=(10.0, 10.0, 20.0, 20.0),
        confidence=0.9,
        timestamp=0.0,
    )
    result = service.detect([detection], [DetectorTrack(track_id="1", detections=[detection])])
    assert len(result) == 1
    assert result[0].detector == "restricted_area"
    assert result[0].label == "person"
    assert result[0].score == 0.9
    assert result[0].track_id == "1"
