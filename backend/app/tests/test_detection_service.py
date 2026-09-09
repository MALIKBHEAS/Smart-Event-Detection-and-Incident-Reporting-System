from __future__ import annotations

from app.domain.detection import BaseDetector, RawDetection
from app.plugins.cv.yolo_detector import YOLODetector
from app.services.detection_service import DetectionService
from app.workers.detectors import (
    BaseEventDetector,
    LineCrossingDetector,
    LoiteringDetector,
    RestrictedAreaDetector,
    SuspiciousObjectDetector,
)


class FakeRawDetector(BaseDetector):
    def detect(self, frame: object, conf: float = 0.5) -> list[RawDetection]:
        return [
            RawDetection(
                id="1",
                class_id=0,
                class_name="person",
                label="person",
                confidence=0.9,
                bbox=(10.0, 10.0, 20.0, 20.0),
                timestamp=1.0,
            )
        ]


def test_detection_service_wraps_base_detector() -> None:
    service = DetectionService(FakeRawDetector())
    results = service.detect(frame=object(), confidence_threshold=0.5)
    assert len(results) == 1
    assert isinstance(results[0], RawDetection)
    assert results[0].label == "person"
    assert results[0].confidence == 0.9


def test_yolo_detector_is_base_detector_subclass() -> None:
    assert issubclass(YOLODetector, BaseDetector)


def test_event_detector_plugins_inherit_base_event_detector() -> None:
    for detector_class in [
        RestrictedAreaDetector,
        LineCrossingDetector,
        LoiteringDetector,
        SuspiciousObjectDetector,
    ]:
        assert issubclass(detector_class, BaseEventDetector)
