from __future__ import annotations

import logging
import time
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

YOLO: Any = None
try:
    from ultralytics import YOLO as UltralyticsYOLO
    YOLO = UltralyticsYOLO
except ImportError:  # pragma: no cover
    pass

torch: Any = None
try:
    import torch as _torch
    torch = _torch
except ImportError:  # pragma: no cover
    pass


from app.domain.detection import BaseDetector, RawDetection

ALLOWED_CLASSES = {
    "person",
    "car",
    "truck",
    "motorcycle",
    "bicycle",
    "backpack",
    "suitcase",
}


class YOLODetector(BaseDetector):
    """YOLO-based detector that returns bounding boxes, labels, and confidence."""

    def __init__(
        self,
        device: Optional[str] = None,
        model_path: str = "yolov8n.pt",
        target_classes: Optional[set[str]] = None,
    ) -> None:
        self.device = self._choose_device(device)
        self.model_path = model_path
        self.target_classes = target_classes if target_classes is not None else ALLOWED_CLASSES
        self.model = None

        if YOLO is None:
            logger.warning("ultralytics YOLO support is not installed; YOLODetector will return no detections")
            return

        try:
            self.model = YOLO(model_path)
            try:
                self.model.to(self.device)
            except Exception:
                logger.warning("Failed to move YOLO model to device %s; continuing on default device", self.device)
        except Exception as exc:
            logger.warning("Could not initialize YOLO model %s: %s", model_path, exc)
            self.model = None

    def _choose_device(self, device: Optional[str]) -> str:
        if device and device.lower() != "auto":
            return device
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def detect(self, frame: Any, conf: float = 0.5) -> List[RawDetection]:
        if self.model is None:
            return []

        try:
            results = self.model(frame, conf=conf)
        except Exception as exc:
            logger.exception("YOLO inference failed: %s", exc)
            return []

        detections: List[RawDetection] = []
        now_ts = float(time.time())
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            names = getattr(self.model, "names", {}) or getattr(result, "names", {}) or {}
            try:
                xyxy = boxes.xyxy.cpu().numpy()
                confs = boxes.conf.cpu().numpy()
                classes = boxes.cls.cpu().numpy().astype(int)
            except Exception:
                continue

            for bbox, confidence, class_id in zip(xyxy, confs, classes):
                raw_name = names.get(int(class_id), str(class_id))
                class_name = str(raw_name).lower()
                if class_name not in self.target_classes:
                    continue

                x1, y1, x2, y2 = bbox.tolist()
                detections.append(
                    RawDetection(
                        id=None,
                        class_id=int(class_id),
                        class_name=class_name,
                        label=class_name,
                        confidence=float(confidence),
                        bbox=(float(x1), float(y1), float(x2 - x1), float(y2 - y1)),
                        timestamp=now_ts,
                    )
                )
        return detections
