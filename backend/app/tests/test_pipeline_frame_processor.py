from __future__ import annotations

from app.domain.detection import RawDetection
from app.services.detection_service import DetectionService
from app.services.event_detector_service import EventDetectorService
from app.workers.pipeline.context import FrameContext
from app.workers.pipeline.frame_processor import DetectionFrameProcessor
from app.workers.pipeline.protocols import FrameProcessorProtocol
from app.workers.tracker import CentroidTracker


class FakeDetector:
    def detect(self, frame: object, conf: float = 0.5) -> list[RawDetection]:
        return [
            RawDetection(
                id="1",
                class_id=0,
                class_name="person",
                label="person",
                confidence=0.95,
                bbox=(10.0, 10.0, 20.0, 20.0),
                timestamp=1.0,
            ),
            RawDetection(
                id="2",
                class_id=1,
                class_name="bag",
                label="bag",
                confidence=0.2,
                bbox=(50.0, 50.0, 10.0, 10.0),
                timestamp=1.0,
            ),
        ]


def test_frame_processor_filters_by_confidence() -> None:
    processor = DetectionFrameProcessor(
        DetectionService(FakeDetector()),
        EventDetectorService([]),
        CentroidTracker(),
        confidence_threshold=0.5,
    )
    processed = processor.process(
        FrameContext(timestamp=1.0, frame=object(), camera_id=1, camera_name="cam")
    )
    assert len(processed.raw_detections) == 2
    assert len(processed.filtered_detections) == 1
    assert processed.filtered_detections[0].label == "person"


def test_frame_processor_runs_event_detectors() -> None:
    event_config = [
        {
            "name": "restricted_area",
            "areas": {"zone": [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]},
        }
    ]
    processor = DetectionFrameProcessor(
        DetectionService(FakeDetector()),
        EventDetectorService(event_config),
        CentroidTracker(),
        confidence_threshold=0.5,
    )
    processed = processor.process(
        FrameContext(timestamp=2.0, frame=object(), camera_id=2, camera_name="cam2")
    )
    assert len(processed.events) >= 1
    assert processed.events[0].detector == "restricted_area"


def test_frame_processor_process_detections_skips_cv_detector() -> None:
    processor = DetectionFrameProcessor(
        DetectionService(FakeDetector()),
        EventDetectorService([]),
        CentroidTracker(),
        confidence_threshold=0.5,
    )
    prefiltered = [
        RawDetection(
            id="9",
            class_id=0,
            class_name="car",
            label="car",
            confidence=0.88,
            bbox=(5.0, 5.0, 15.0, 15.0),
            timestamp=3.0,
        )
    ]
    processed = processor.process_detections(
        FrameContext(timestamp=3.0, frame=object(), camera_id=3, camera_name="cam3"),
        prefiltered,
    )
    assert processed.raw_detections == prefiltered
    assert len(processed.filtered_detections) == 1
    assert processed.filtered_detections[0].label == "car"
    assert len(processed.detector_objects) == 1


def test_frame_processor_implements_protocol() -> None:
    processor = DetectionFrameProcessor(
        DetectionService(FakeDetector()),
        EventDetectorService([]),
        CentroidTracker(),
    )
    assert isinstance(processor, FrameProcessorProtocol)
