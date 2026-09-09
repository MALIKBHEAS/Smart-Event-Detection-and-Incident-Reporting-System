from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
from app.domain.detection import BaseDetector, DetectionResult
from app.plugins.cv.yolo_detector import YOLODetector


def test_yolo_detector_filters_allowed_classes(monkeypatch) -> None:
    fake_model = MagicMock()
    fake_model.names = {0: "person", 1: "dog", 2: "car", 3: "backpack"}

    fake_boxes = MagicMock()
    fake_boxes.xyxy.cpu().numpy.return_value = np.array([
        [10.0, 20.0, 50.0, 80.0],
        [5.0, 5.0, 15.0, 15.0],
        [100.0, 100.0, 200.0, 150.0],
        [30.0, 30.0, 45.0, 45.0],
    ])
    fake_boxes.conf.cpu().numpy.return_value = np.array([0.95, 0.85, 0.90, 0.75])
    fake_boxes.cls.cpu().numpy().astype.return_value = np.array([0, 1, 2, 3])

    fake_result = MagicMock()
    fake_result.boxes = fake_boxes
    fake_result.names = fake_model.names
    fake_model.return_value = [fake_result]

    monkeypatch.setattr("app.plugins.cv.yolo_detector.YOLO", lambda path: fake_model)

    detector = YOLODetector(model_path="fake.pt")
    detections = detector.detect(frame=object(), conf=0.5)

    # dog (class_id=1) should be filtered out
    class_names = [d.class_name for d in detections]
    assert "person" in class_names
    assert "car" in class_names
    assert "backpack" in class_names
    assert "dog" not in class_names
    assert len(detections) == 3


def test_yolo_detector_implements_protocol() -> None:
    detector = YOLODetector()
    assert isinstance(detector, BaseDetector)


def test_detection_result_model() -> None:
    res = DetectionResult(
        class_id=0,
        class_name="person",
        confidence=0.92,
        bounding_box=(10.0, 10.0, 40.0, 60.0),
        timestamp=100.0,
        camera_id=1,
    )
    assert res.class_id == 0
    assert res.class_name == "person"
    assert res.label == "person"
    assert res.confidence == 0.92
    assert res.score == 0.92
    assert res.bounding_box == (10.0, 10.0, 40.0, 60.0)
    assert res.camera_id == 1
