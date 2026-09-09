from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, cast

from app.domain.detection import DetectionResult, RawDetection
from app.services.detection_service import DetectionService
from app.services.event_detector_service import EventDetectorService
from app.services.health_monitor.registry import HealthRegistry
from app.workers.detectors import Detection as DetectorDetection
from app.workers.detectors import DetectionResult as WorkerDetectionResult
from app.workers.detectors import Track as DetectorTrack
from app.workers.pipeline.context import FrameContext, ProcessedFrame
from app.workers.pipeline.protocols import FrameProcessorProtocol
from app.workers.tracker import Track as TrackerTrack

logger = logging.getLogger(__name__)


class DetectionFrameProcessor(FrameProcessorProtocol):
    """Orchestrates detection, tracking, and event detection for one frame."""

    def __init__(
        self,
        detection_service: DetectionService,
        event_detector_service: EventDetectorService,
        tracker: object,
        *,
        confidence_threshold: float = 0.5,
        track_history_size: int = 8,
    ) -> None:
        self._detection_service = detection_service
        self._event_detector_service = event_detector_service
        self._tracker: Any = tracker
        self._confidence_threshold = confidence_threshold
        self._track_history_size = track_history_size
        self._track_history: Dict[int, List[DetectorDetection]] = {}

    @property
    def confidence_threshold(self) -> float:
        return self._confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        self._confidence_threshold = float(value)

    def process_detections(self, context: FrameContext, detections: List[RawDetection]) -> ProcessedFrame:
        """Process pre-filtered detections without re-running the CV detector."""
        filtered = [
            detection
            for detection in detections
            if float(getattr(detection, "confidence", 0.0)) >= self._confidence_threshold
        ]
        detector_objects = self._to_detector_objects(filtered, context.timestamp)
        tracks, tracked_objects = self._update_tracks(detector_objects, context)
        events = self._run_event_detectors(detector_objects, tracks)
        return ProcessedFrame(
            timestamp=context.timestamp,
            frame=context.frame,
            raw_detections=list(detections),
            filtered_detections=filtered,
            detector_objects=detector_objects,
            tracks=tracks,
            tracked_objects=tracked_objects,
            events=events,
        )

    def process(self, context: FrameContext) -> ProcessedFrame:
        raw_detections = self._run_detection(context.frame)
        filtered = [
            detection
            for detection in raw_detections
            if float(getattr(detection, "confidence", 0.0)) >= self._confidence_threshold
        ]
        detector_objects = self._to_detector_objects(filtered, context.timestamp)
        tracks, tracked_objects = self._update_tracks(detector_objects, context)
        events = self._run_event_detectors(detector_objects, tracks)
        return ProcessedFrame(
            timestamp=context.timestamp,
            frame=context.frame,
            raw_detections=raw_detections,
            filtered_detections=filtered,
            detector_objects=detector_objects,
            tracks=tracks,
            tracked_objects=tracked_objects,
            events=events,
        )

    def _run_detection(self, frame: Any) -> List[RawDetection]:
        try:
            return self._detection_service.detect(frame, confidence_threshold=self._confidence_threshold)
        except Exception:
            logger.exception("Detection service failed during frame processing")
            return []

    def _to_detector_objects(
        self,
        detections: List[RawDetection],
        timestamp: float,
    ) -> List[DetectorDetection]:
        detector_objects: List[DetectorDetection] = []
        for index, detection in enumerate(detections):
            try:
                bbox = self._bbox_from_detection(detection)
            except Exception:
                continue
            if isinstance(detection, RawDetection):
                detector_objects.append(
                    DetectorDetection(
                        id=str(detection.id) if detection.id is not None else str(index),
                        label=detection.label or detection.class_name or "unknown",
                        bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                        confidence=float(detection.confidence),
                        timestamp=float(detection.timestamp),
                        extra={
                            **detection.extra,
                            "class_id": detection.class_id,
                            "class_name": detection.class_name,
                        },
                    )
                )
            else:
                detection_dict = cast(Dict[str, Any], detection)
                detector_objects.append(
                    DetectorDetection(
                        id=str(detection_dict.get("id") or detection_dict.get("track_id") or index),
                        label=str(detection_dict.get("class") or detection_dict.get("label") or "unknown"),
                        bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                        confidence=float(detection_dict.get("confidence", 0.0)),
                        timestamp=float(timestamp),
                        extra={
                            key: value
                            for key, value in detection_dict.items()
                            if key
                            not in {
                                "bbox",
                                "box",
                                "x",
                                "y",
                                "w",
                                "h",
                                "width",
                                "height",
                                "class",
                                "label",
                                "confidence",
                                "id",
                                "track_id",
                            }
                        },
                    )
                )
        return detector_objects

    def _update_tracks(
        self,
        detector_objects: List[DetectorDetection],
        context: FrameContext,
    ) -> Tuple[List[DetectorTrack], List[TrackerTrack]]:
        rects: List[Tuple[int, int, int, int]] = []
        dets_for_tracker: List[Dict[str, Any]] = []
        for detection in detector_objects:
            x, y, w, h = detection.bbox
            bbox_xyxy = (int(x), int(y), int(x + w), int(y + h))
            rects.append(bbox_xyxy)
            dets_for_tracker.append(
                {
                    "bbox": bbox_xyxy,
                    "score": detection.confidence,
                    "class_id": detection.extra.get("class_id"),
                    "class_name": detection.extra.get("class_name") or detection.label,
                }
            )

        try:
            tracked_objects = self._tracker.update(dets_for_tracker)
        except Exception:
            logger.exception("Tracker update failed for camera %s", context.camera_name)
            try:
                # Some trackers (e.g. a legacy plain-bbox tracker) may not
                # accept the dict form above; fall back to bare rects so a
                # non-enriched tracker keeps working unmodified.
                tracked_objects = self._tracker.update(rects)
            except Exception:
                logger.exception("Tracker update failed for camera %s (bbox fallback)", context.camera_name)
                tracked_objects = {index: rect for index, rect in enumerate(rects)}

        tracks: List[DetectorTrack] = []
        tracked_objects_out: List[TrackerTrack] = []
        if isinstance(tracked_objects, dict):
            items = list(tracked_objects.items())
        else:
            items = [(track.track_id, track.bbox) for track in tracked_objects]
            tracked_objects_out = list(tracked_objects)

        for obj_id, bbox in items:
            track_history = self._track_history.setdefault(obj_id, [])
            matched = self._find_matching_detection(detector_objects, bbox)
            if matched is not None:
                track_history.append(matched)
                if len(track_history) > self._track_history_size:
                    track_history.pop(0)
            tracks.append(DetectorTrack(track_id=str(obj_id), detections=list(track_history)))
        return tracks, tracked_objects_out

    def _run_event_detectors(
        self,
        detector_objects: List[DetectorDetection],
        tracks: List[DetectorTrack],
    ) -> List[DetectionResult]:
        events = self._event_detector_service.detect(detector_objects, tracks)
        if events:
            return events
        return [
            WorkerDetectionResult(
                detector="detection",
                detection_id=detection.id,
                track_id=str(index),
                label=detection.label,
                score=detection.confidence,
                metadata={"bbox": detection.bbox},
            )
            for index, detection in enumerate(detector_objects)
        ]

    @staticmethod
    def _bbox_from_detection(detection: RawDetection | Dict[str, Any]) -> Tuple[int, int, int, int]:
        if isinstance(detection, RawDetection):
            x, y, w, h = detection.bbox
            return int(x), int(y), int(w), int(h)
        bbox = detection.get("bbox") or detection.get("box")
        if bbox is None:
            x = int(detection.get("x", 0))
            y = int(detection.get("y", 0))
            w = int(detection.get("w", detection.get("width", 0)))
            h = int(detection.get("h", detection.get("height", 0)))
            bbox = (x, y, w, h)
        return int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

    @staticmethod
    def _normalize_bbox(bbox: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        if x2 < x1:
            x2 = x1 + x2
        if y2 < y1:
            y2 = y1 + y2
        return x1, y1, x2, y2

    @staticmethod
    def _iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        if inter_w == 0 or inter_h == 0:
            return 0.0
        inter_area = inter_w * inter_h
        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union_area = area_a + area_b - inter_area
        if union_area <= 0:
            return 0.0
        return inter_area / union_area

    def _find_matching_detection(
        self,
        detections: List[DetectorDetection],
        bbox_xyxy: Tuple[int, int, int, int],
    ) -> Optional[DetectorDetection]:
        best: Optional[DetectorDetection] = None
        best_iou = 0.0
        for detection in detections:
            try:
                det_xyxy = self._normalize_bbox(
                    cast(Tuple[int, int, int, int], tuple(int(value) for value in detection.bbox))
                    if len(detection.bbox) == 4
                    else (0, 0, 0, 0)
                )
            except Exception:
                continue
            score = self._iou(det_xyxy, bbox_xyxy)
            if score > best_iou:
                best_iou = score
                best = detection
        return best if best_iou >= 0.1 else None
