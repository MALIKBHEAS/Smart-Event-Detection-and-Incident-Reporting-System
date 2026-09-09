from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.workers.detectors import (
    BaseEventDetector,
    DetectionResult,
    LineCrossingDetector,
    LoiteringDetector,
    RestrictedAreaDetector,
    SuspiciousObjectDetector,
)
from app.workers.detectors import (
    Detection as DetectorDetection,
)
from app.workers.detectors import (
    Track as DetectorTrack,
)

logger = logging.getLogger(__name__)


_EVENT_DETECTOR_MAP: Dict[str, type] = {
    "restricted_area": RestrictedAreaDetector,
    "restricted-area": RestrictedAreaDetector,
    "line_crossing": LineCrossingDetector,
    "line-crossing": LineCrossingDetector,
    "loitering": LoiteringDetector,
    "suspicious_object": SuspiciousObjectDetector,
    "suspicious-object": SuspiciousObjectDetector,
}


def _normalize_detector_config(config: Any) -> List[Dict[str, Any]]:
    if config is None:
        return []
    if isinstance(config, dict) and "event_detectors" in config:
        config = config["event_detectors"]
    if isinstance(config, str):
        return [{"name": config}]
    if isinstance(config, dict):
        return [config]
    if isinstance(config, list):
        return [item for item in config if item is not None]
    return []


class EventDetectorService:
    """Service that constructs and runs event detector plugins."""

    def __init__(self, configs: Any = None) -> None:
        self.detectors = self._build_detectors(configs)

    @property
    def has_detectors(self) -> bool:
        return len(self.detectors) > 0

    def _build_detectors(self, configs: Any) -> List[BaseEventDetector]:
        detectors: List[BaseEventDetector] = []
        normalized = _normalize_detector_config(configs)
        for item in normalized:
            if isinstance(item, str):
                name = item
                params: Dict[str, Any] = {}
            elif isinstance(item, dict):
                name = item.get("name") or item.get("type")
                if name is None:
                    continue
                params = item.get("config") or item.get("params") or {
                    k: v for k, v in item.items() if k not in ("name", "type")
                }
            else:
                continue

            if not isinstance(name, str):
                continue
            detector_cls = _EVENT_DETECTOR_MAP.get(name.lower())
            if detector_cls is None:
                logger.warning("Unknown event detector '%s', skipping", name)
                continue

            try:
                detectors.append(detector_cls(**(params or {})))
            except Exception:
                logger.exception("Failed to initialize event detector '%s' with params %s", name, params)
        return detectors

    def detect(
        self,
        detections: List[DetectorDetection],
        tracks: List[DetectorTrack],
    ) -> List[DetectionResult]:
        results: List[DetectionResult] = []
        for detector in self.detectors:
            try:
                detector_results = detector.detect(detections, tracks)
                if detector_results:
                    results.extend(detector_results)
            except Exception:
                logger.exception("Event detector %s failed during detection", type(detector).__name__)
        return results

    def append_detector(self, detector: BaseEventDetector) -> None:
        self.detectors.append(detector)
