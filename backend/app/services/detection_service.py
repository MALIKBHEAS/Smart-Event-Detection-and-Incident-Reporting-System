from __future__ import annotations

import logging
from typing import Any, List, Optional

from app.domain.detection import BaseDetector, RawDetection
from app.plugins.cv import YOLODetector

logger = logging.getLogger(__name__)


class YOLODetectionService:
    """Service wrapper around a YOLO detector plugin.

    This service isolates YOLO model loading and inference so the worker can
    remain focused on pipeline orchestration.
    """

    def __init__(self, device: Optional[str] = None, model_path: str = "yolov8n.pt") -> None:
        self.device = device
        self.model_path = model_path
        self.detector: Optional[BaseDetector] = None
        self._initialize_detector()

    def _initialize_detector(self) -> None:
        if YOLODetector is None:
            logger.warning("YOLO detector plugin is not available; detection will be disabled")
            return

        try:
            self.detector = YOLODetector(device=self.device, model_path=self.model_path)
            logger.debug("YOLODetectionService loaded model %s on device %s", self.model_path, self.device)
        except Exception as exc:
            logger.exception("Failed to initialize YOLODetector: %s", exc)
            self.detector = None

    def detect(self, frame: Any, confidence_threshold: float = 0.5) -> List[RawDetection]:
        if self.detector is None:
            return []

        try:
            return self.detector.detect(frame, conf=confidence_threshold) or []
        except Exception:
            logger.exception("YOLODetectionService failed during inference")
            return []


class DetectionService:
    """Generic detection service wrapper.

    Allows future detector implementations to be added with the same interface.
    """

    def __init__(self, detector: Optional[BaseDetector] = None) -> None:
       self.detector = detector

    def detect(self, frame: Any, confidence_threshold: float = 0.5) -> List[RawDetection]:
       if self.detector is None:
           return []
       if hasattr(self.detector, "detect"):
           return self.detector.detect(frame, conf=confidence_threshold) or []
       if callable(self.detector):
           return self.detector(frame) or []
       return []
