from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.detection import DetectionResult, RawDetection
from app.workers.detectors import Detection as DetectorDetection
from app.workers.detectors import Track as DetectorTrack
from app.workers.tracker import Track as TrackerTrack


@dataclass
class FrameContext:
    """Input context for a single frame entering the detection pipeline."""

    timestamp: float
    frame: Any
    camera_id: int
    camera_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedFrame:
    """Output of the detection pipeline for a single frame."""

    timestamp: float
    frame: Any
    raw_detections: List[RawDetection] = field(default_factory=list)
    filtered_detections: List[RawDetection] = field(default_factory=list)
    detector_objects: List[DetectorDetection] = field(default_factory=list)
    tracks: List[DetectorTrack] = field(default_factory=list)
    # Rich tracker output (bbox, class_name, confidence, track_id) for
    # consumers that need it directly, e.g. Live Monitoring overlays. Kept
    # separate from `tracks` above (which is the event-detector-facing
    # history format) to avoid touching that existing contract.
    tracked_objects: List[TrackerTrack] = field(default_factory=list)
    events: List[DetectionResult] = field(default_factory=list)
    screenshot_path: Optional[str] = None
