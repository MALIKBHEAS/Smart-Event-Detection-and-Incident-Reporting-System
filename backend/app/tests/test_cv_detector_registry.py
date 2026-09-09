from __future__ import annotations

import pytest
from app.domain.detection import BaseDetector, RawDetection
from app.workers.pipeline.cv_detector_registry import (
    NoOpDetector,
    default_detector,
    get_detector,
    list_registered_detectors,
    register_detector,
)


class EchoDetector:
    def detect(self, frame: object, conf: float = 0.5) -> list[RawDetection]:
        return [
            RawDetection(
                id="echo",
                class_id=0,
                class_name="echo",
                label="echo",
                confidence=0.99,
                bbox=(1.0, 2.0, 3.0, 4.0),
                timestamp=0.0,
            )
        ]


def test_noop_detector_returns_empty_list() -> None:
    detector = NoOpDetector()
    assert detector.detect(object()) == []


def test_builtin_detectors_are_registered() -> None:
    names = list_registered_detectors()
    assert "noop" in names
    assert "yolo" in names


def test_get_detector_noop() -> None:
    detector = get_detector("noop")
    assert isinstance(detector, NoOpDetector)
    assert detector.detect(object()) == []


def test_get_detector_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown CV detector"):
        get_detector("does-not-exist")


def test_register_custom_detector() -> None:
    register_detector("echo", lambda **kwargs: EchoDetector())
    detector = get_detector("echo")
    assert isinstance(detector, EchoDetector)
    results = detector.detect(object())
    assert len(results) == 1
    assert results[0].label == "echo"


def test_default_detector_returns_base_detector() -> None:
    detector = default_detector()
    assert isinstance(detector, BaseDetector)
