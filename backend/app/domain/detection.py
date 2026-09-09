from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

BBox = Tuple[float, float, float, float]


@dataclass
class RawDetection:
    """Raw detection result from a CV detector implementation."""

    id: Optional[str]
    class_id: Optional[int]
    class_name: str
    label: str
    confidence: float
    bbox: BBox
    timestamp: float
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectionResult:
    """Structured detection result containing class info, confidence, bounding box, timestamp, and camera_id."""

    class_id: Optional[int] = None
    class_name: str = ""
    confidence: float = 0.0
    bounding_box: BBox = (0.0, 0.0, 0.0, 0.0)
    timestamp: float = 0.0
    camera_id: Optional[int] = None

    # Event detector compatibility fields
    detector: str = "yolo"
    detection_id: Optional[str] = None
    track_id: Optional[str] = None
    label: str = ""
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.label and self.class_name:
            self.label = self.class_name
        elif not self.class_name and self.label:
            self.class_name = self.label
        if self.score == 0.0 and self.confidence != 0.0:
            self.score = self.confidence
        elif self.confidence == 0.0 and self.score != 0.0:
            self.confidence = self.score
        if "bbox" in self.metadata and self.bounding_box == (0.0, 0.0, 0.0, 0.0):
            self.bounding_box = self.metadata["bbox"]
        elif self.bounding_box != (0.0, 0.0, 0.0, 0.0) and "bbox" not in self.metadata:
            self.metadata["bbox"] = self.bounding_box


@runtime_checkable
class BaseDetector(Protocol):
    """Protocol for vision detectors used by the detection pipeline."""

    def detect(self, frame: Any, conf: float = 0.5) -> List[RawDetection]:
        ...
