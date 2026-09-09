"""
Detectors module

Provides a DetectorProtocol and a set of simple, configurable detectors:
- RestrictedAreaDetector
- LineCrossingDetector
- LoiteringDetector
- SuspiciousObjectDetector

Each detector is stateless where reasonable, accepts lists of Detection and Track
objects and returns a list of DetectionResult dictionaries describing events.

The implementations are intentionally compact but production-ready (configurable
thresholds, clear typing, minimal external dependencies).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.domain.detection import DetectionResult

# Basic types ---------------------------------------------------------------

Timestamp = float  # seconds since epoch
BBox = Tuple[float, float, float, float]  # x, y, w, h
Point = Tuple[float, float]


@dataclass
class Detection:
    """Represents a single object detection (one frame).

    Attributes:
        id: Optional identifier provided by upstream detector (may be None).
        label: Class label.
        bbox: Bounding box (x, y, w, h) in pixels or normalized units — detectors
            treat coordinates consistently with the rest of the pipeline.
        confidence: Class confidence score [0..1].
        timestamp: Detection time (seconds since epoch). If omitted, uses now().
        extra: Arbitrary additional data.
    """
    id: Optional[str]
    label: str
    bbox: BBox
    confidence: float
    timestamp: Timestamp = field(default_factory=time.time)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Track:
    """Represent a track (sequence of detections associated to the same object).

    Attributes:
        track_id: Unique id for the track.
        detections: List of Detection objects in chronological order.
    """
    track_id: str
    detections: List[Detection]


# Detector Protocol ---------------------------------------------------------


class DetectorProtocol(Protocol):
    """Protocol for detectors used by the workers.

    Implementations must provide a detect method that accepts a list of
    detections and a list of tracks, and returns a list of DetectionResult.
    """

    def detect(self, detections: List[Detection], tracks: List[Track]) -> List[DetectionResult]:
        ...


class BaseEventDetector:
    """Base class for event detector plugins."""

    def detect(self, detections: List[Detection], tracks: List[Track]) -> List[DetectionResult]:
        raise NotImplementedError


# Helper geometry functions -------------------------------------------------


def bbox_to_centroid(bbox: BBox) -> Point:
    x, y, w, h = bbox
    return (x + w / 2.0, y + h / 2.0)


def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
    """Ray-casting algorithm to determine if point is inside polygon.

    polygon: list of (x, y) tuples. Works for non-self-intersecting polygons.
    """
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[(i + 1) % n]
        intersect = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        )
        if intersect:
            inside = not inside
    return inside


def seg_intersect(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
    """Check if segments a1-a2 and b1-b2 intersect (excluding colinear edge cases).
    Uses orientation tests.
    """
    def orient(p: Point, q: Point, r: Point) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_segment(p: Point, q: Point, r: Point) -> bool:
        return min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])

    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)

    if o1 == 0 and on_segment(a1, b1, a2):
        return True
    if o2 == 0 and on_segment(a1, b2, a2):
        return True
    if o3 == 0 and on_segment(b1, a1, b2):
        return True
    if o4 == 0 and on_segment(b1, a2, b2):
        return True

    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def centroid_distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def iou(b1: BBox, b2: BBox) -> float:
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    xa = max(x1, x2)
    ya = max(y1, y2)
    xb = min(x1 + w1, x2 + w2)
    yb = min(y1 + h1, y2 + h2)
    inter_w = max(0.0, xb - xa)
    inter_h = max(0.0, yb - ya)
    inter = inter_w * inter_h
    union = w1 * h1 + w2 * h2 - inter
    if union <= 0:
        return 0.0
    return inter / union


# Detector implementations --------------------------------------------------


class RestrictedAreaDetector(BaseEventDetector):
    """Detects when detections (or tracks) appear inside configured polygonal
    restricted areas.

    Configurable parameters:
        areas: Dict[name, polygon] where polygon is a list of (x,y) points.
        min_confidence: ignore detections below this confidence.
        require_track: if True, only report when a track is present for the
            detection (helps reduce duplicates when detectors generate noise).
    """

    def __init__(
        self,
        areas: Dict[str, List[Point]] | dict,
        min_confidence: float = 0.3,
        require_track: bool = False,
    ) -> None:
        # Support two initialization styles:
        # 1) a mapping of name -> polygon: {'area1': [(x,y), ...], ...}
        # 2) a config dict like {'areas': [{ 'id': 'a1', 'name': 'n', 'polygon': [...] }, ...]}
        if isinstance(areas, dict) and 'areas' in areas and isinstance(areas['areas'], list):
            parsed: Dict[str, List[Point]] = {}
            for a in areas['areas']:
                if isinstance(a, dict):
                    name = a.get('id') or a.get('name') or str(len(parsed) + 1)
                    poly = a.get('polygon') or a.get('points') or []
                elif isinstance(a, (list, tuple)) and len(a) >= 2:
                    name = str(len(parsed) + 1)
                    poly = a[1]
                else:
                    # skip invalid area entries
                    continue
                parsed[name] = poly
            self.areas = parsed
        elif isinstance(areas, dict) and all(isinstance(v, list) for v in areas.values()):
            # assume mapping name->polygon
            self.areas = areas
        else:
            # fallback: attempt to coerce a sequence
            raise ValueError("Unsupported areas configuration for RestrictedAreaDetector")
        self.min_confidence = float(min_confidence)
        self.require_track = require_track

    def detect(self, detections: List[Detection], tracks: List[Track]) -> List[DetectionResult]:
        results: List[DetectionResult] = []
        # Build a mapping detection.id -> track for quick lookup if requested
        detid_to_track: Dict[Optional[str], str] = {}
        for t in tracks:
            if t.detections:
                # assume latest detection references the same id
                latest = t.detections[-1]
                detid_to_track[latest.id] = t.track_id

        processed_ids = set()
        for det in detections:
            if det.confidence < self.min_confidence:
                continue
            if self.require_track and det.id not in detid_to_track:
                continue
            centroid = bbox_to_centroid(det.bbox)
            for name, poly in self.areas.items():
                if point_in_polygon(centroid, poly):
                    results.append(
                        DetectionResult(
                            detector="restricted_area",
                            detection_id=det.id,
                            track_id=detid_to_track.get(det.id),
                            label=det.label,
                            score=det.confidence,
                            metadata={"area_id": name},
                        )
                    )
            processed_ids.add(det.id)

        # Also consider latest detection from tracks even if no raw detections were
        # provided (some pipelines pass only track summaries).
        for t in tracks:
            if not getattr(t, 'detections', None):
                continue
            latest = t.detections[-1]
            if latest.id in processed_ids:
                continue
            if latest.confidence < self.min_confidence:
                continue
            if self.require_track and latest.id not in detid_to_track:
                continue
            centroid = bbox_to_centroid(latest.bbox)
            for name, poly in self.areas.items():
                if point_in_polygon(centroid, poly):
                    results.append(
                        DetectionResult(
                            detector="restricted_area",
                            detection_id=latest.id,
                            track_id=t.track_id,
                            label=latest.label,
                            score=latest.confidence,
                            metadata={"area_id": name},
                        )
                    )
        return results

    # Backwards-compatible alias used by some worker code/tests
    def update(self, detections: List[Detection], tracks: List[Track], frame: Any = None, timestamp: Optional[float] = None) -> List[dict]:
        # Normalize incoming track representations: accept both detectors.Track
        # (which contain .detections) and lightweight tracker.Track objects
        # (which typically have .track_id and .bbox).
        normalized: List[Track] = []
        ts = timestamp or time.time()
        for t in tracks:
            if hasattr(t, 'detections'):
                normalized.append(t)
                continue
            # try to build a minimal Detection from tracker.Track-like object
            tbbox = getattr(t, 'bbox', None)
            tid = getattr(t, 'track_id', getattr(t, 'id', None))
            if tbbox is None:
                normalized.append(Track(track_id=str(tid), detections=[]))
                continue
            # tbbox may be (x1,y1,x2,y2) from tracker.Track; convert to (x,y,w,h)
            try:
                x1, y1, x2, y2 = tbbox
                w = float(x2) - float(x1)
                h = float(y2) - float(y1)
                det = Detection(id=None, label='', bbox=(float(x1), float(y1), w, h), confidence=1.0, timestamp=ts)
                normalized.append(Track(track_id=str(tid), detections=[det]))
            except Exception:
                normalized.append(Track(track_id=str(tid), detections=[]))
        # Run detection logic
        results = self.detect(detections, normalized)
        # Convert DetectionResult objects into legacy dict events expected by
        # existing worker code and tests.
        out: List[dict] = []
        for r in results:
            payload = {
                'detection_id': r.detection_id,
                'track_id': int(r.track_id) if r.track_id is not None else None,
                'label': r.label,
                'score': r.score,
            }
            if r.metadata:
                payload.update(r.metadata)
            evt_type = 'restricted_area_intrusion' if r.detector == 'restricted_area' else r.detector
            out.append({'type': evt_type, 'payload': payload})
        return out


class LineCrossingDetector(BaseEventDetector):
    """Detects when a track crosses a configured line.

    Configurable parameters:
        lines: Dict[name, (p1,p2)] where p1,p2 are points describing the line.
        min_detections: Minimum two detections in track history to test crossing.
        require_direction: None for any crossing, or 'p1_to_p2'/'p2_to_p1' to
            require a particular direction.
    """

    def __init__(
        self,
        lines: Dict[str, Tuple[Point, Point]] | dict,
        min_detections: int = 2,
        require_direction: Optional[str] = None,
    ) -> None:
        # Support config style: {'lines': [ { 'id': 'l1', 'p1':(x,y), 'p2':(x,y), 'direction': 'both' }, ... ]}
        if isinstance(lines, dict) and 'lines' in lines and isinstance(lines['lines'], list):
            parsed: Dict[str, Tuple[Point, Point]] = {}
            for l in lines['lines']:
                name = l.get('id') or l.get('name') or str(len(parsed) + 1)
                p1 = l.get('p1')
                p2 = l.get('p2')
                if p1 is None or p2 is None:
                    raise ValueError('Line entries must include p1 and p2')
                # ensure tuples of floats
                p1t: Point = (float(p1[0]), float(p1[1]))
                p2t: Point = (float(p2[0]), float(p2[1]))
                parsed[name] = (p1t, p2t)
            self.lines = parsed
        elif isinstance(lines, dict) and all(isinstance(v, tuple) or isinstance(v, list) for v in lines.values()):
            parsed = {}
            for k, v in lines.items():
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    p1_raw, p2_raw = v[0], v[1]
                    p1t = (float(p1_raw[0]), float(p1_raw[1]))
                    p2t = (float(p2_raw[0]), float(p2_raw[1]))
                    parsed[k] = (p1t, p2t)
                else:
                    raise ValueError('Invalid line specification')
            self.lines = parsed
        else:
            raise ValueError("Unsupported lines configuration for LineCrossingDetector")
        self.min_detections = max(2, int(min_detections))
        if require_direction not in (None, "p1_to_p2", "p2_to_p1"):
            raise ValueError("require_direction must be None, 'p1_to_p2' or 'p2_to_p1'")
        self.require_direction = require_direction
        # Keep a small per-track history between update() calls so that simple
        # trackers that provide only the latest detection can still detect
        # line crossings across frames.
        self._last_detections: Dict[str, Detection] = {}

    def detect(self, detections: List[Detection], tracks: List[Track]) -> List[DetectionResult]:
        results: List[DetectionResult] = []
        for t in tracks:
            if len(t.detections) < self.min_detections:
                continue
            a = bbox_to_centroid(t.detections[-2].bbox)
            b = bbox_to_centroid(t.detections[-1].bbox)
            for name, (p1, p2) in self.lines.items():
                if seg_intersect(a, b, p1, p2):
                    direction = None
                    # compute direction by projecting movement onto line vector
                    vx, vy = p2[0] - p1[0], p2[1] - p1[1]
                    movx, movy = b[0] - a[0], b[1] - a[1]
                    dot = vx * movx + vy * movy
                    if dot > 0:
                        direction = "p1_to_p2"
                    elif dot < 0:
                        direction = "p2_to_p1"
                    if self.require_direction and self.require_direction != direction:
                        continue
                    # attach info about crossing
                    results.append(
                        DetectionResult(
                            detector="line_crossing",
                            detection_id=t.detections[-1].id,
                            track_id=t.track_id,
                            label=t.detections[-1].label,
                            score=float(t.detections[-1].confidence),
                            metadata={"line": name, "direction": direction},
                        )
                    )
        return results

    # Backwards-compatible alias
    def update(self, detections: List[Detection], tracks: List[Track], frame: Any = None, timestamp: Optional[float] = None) -> List[dict]:
        # Normalize incoming track representations to detectors.Track when needed
        normalized: List[Track] = []
        ts = timestamp or time.time()
        for t in tracks:
            if hasattr(t, 'detections'):
                normalized.append(t)
                continue
            tbbox = getattr(t, 'bbox', None)
            tid = getattr(t, 'track_id', getattr(t, 'id', None))
            if tbbox is None:
                normalized.append(Track(track_id=str(tid), detections=[]))
                continue
            try:
                x1, y1, x2, y2 = tbbox
                w = float(x2) - float(x1)
                h = float(y2) - float(y1)
                det = Detection(id=None, label='', bbox=(float(x1), float(y1), w, h), confidence=1.0, timestamp=ts)
                normalized.append(Track(track_id=str(tid), detections=[det]))
            except Exception:
                normalized.append(Track(track_id=str(tid), detections=[]))
        # Merge with stored previous detection if available to create a short history
        for i, t in enumerate(normalized):
            try:
                tid = str(t.track_id)
            except Exception:
                tid = None
            if tid and tid in self._last_detections and t.detections:
                prev = self._last_detections[tid]
                # create a synthetic track with prev + current detections
                combined = Track(track_id=tid, detections=[prev, t.detections[-1]])
                normalized[i] = combined
        # After preparing normalized tracks, update the stored last detections
        for t in normalized:
            if t.detections:
                self._last_detections[str(t.track_id)] = t.detections[-1]
        results = self.detect(detections, normalized)
        out: List[dict] = []
        for r in results:
            payload = {
                'detection_id': r.detection_id,
                'track_id': int(r.track_id) if r.track_id is not None else None,
                'label': r.label,
                'score': r.score,
            }
            if r.metadata:
                payload.update(r.metadata)
            evt_type = r.detector
            out.append({'type': evt_type, 'payload': payload})
        return out


class LoiteringDetector(BaseEventDetector):
    """Detects loitering: a track that remains within a small area for a
    minimum duration.

    Configurable parameters:
        max_movement_px: maximum centroid movement allowed (pixels) during window.
        min_duration_s: minimum time in seconds to consider loitering.
        lookback: how many seconds into the track history to examine. If None,
            examine the whole track.
    """

    def __init__(self, max_movement_px: float = 20.0, min_duration_s: float = 30.0, lookback: Optional[float] = None) -> None:
        self.max_movement_px = float(max_movement_px)
        self.min_duration_s = float(min_duration_s)
        self.lookback = None if lookback is None else float(lookback)

    def detect(self, detections: List[Detection], tracks: List[Track]) -> List[DetectionResult]:
        now_ts = time.time()
        results: List[DetectionResult] = []
        for t in tracks:
            if not t.detections:
                continue
            # build window of detections based on lookback
            if self.lookback is None:
                window = t.detections
            else:
                cutoff = now_ts - self.lookback
                window = [d for d in t.detections if d.timestamp >= cutoff]
            if len(window) < 2:
                continue
            start_ts = window[0].timestamp
            end_ts = window[-1].timestamp
            duration = end_ts - start_ts
            if duration < self.min_duration_s:
                continue
            # compute max centroid displacement
            centroids = [bbox_to_centroid(d.bbox) for d in window]
            minx = min(c[0] for c in centroids)
            maxx = max(c[0] for c in centroids)
            miny = min(c[1] for c in centroids)
            maxy = max(c[1] for c in centroids)
            span = math.hypot(maxx - minx, maxy - miny)
            if span <= self.max_movement_px:
                results.append(
                    DetectionResult(
                        detector="loitering",
                        detection_id=window[-1].id,
                        track_id=t.track_id,
                        label=window[-1].label,
                        score=float(window[-1].confidence),
                        metadata={"duration_s": duration, "span_px": span},
                    )
                )
        return results

    # Backwards-compatible alias
    def update(self, detections: List[Detection], tracks: List[Track], frame: Any = None, timestamp: Optional[float] = None) -> List[DetectionResult]:
        return self.detect(detections, tracks)


class SuspiciousObjectDetector(BaseEventDetector):
    """Detect suspicious stationary/left-behind objects.

    Strategy (simple):
      - Accept labels considered suspicious (e.g., 'bag', 'backpack').
      - Find detections with those labels that have low movement for a
        configured minimum duration and are not associated with a moving track.

    Configurable parameters:
        suspicious_labels: set of labels to treat as suspicious.
        min_confidence: detection confidence threshold.
        min_duration_s: how long the object must be stationary to consider suspicious.
        max_movement_px: maximum movement allowed for the object to be considered stationary.
        match_track_iou: IoU threshold to consider detection matched to a track (occupied by a person).
    """

    def __init__(
        self,
        suspicious_labels: Optional[List[str]] = None,
        min_confidence: float = 0.3,
        min_duration_s: float = 60.0,
        max_movement_px: float = 10.0,
        match_track_iou: float = 0.3,
    ) -> None:
        self.suspicious_labels = set(suspicious_labels or ["bag", "backpack", "suitcase"])
        self.min_confidence = float(min_confidence)
        self.min_duration_s = float(min_duration_s)
        self.max_movement_px = float(max_movement_px)
        self.match_track_iou = float(match_track_iou)

    def detect(self, detections: List[Detection], tracks: List[Track]) -> List[DetectionResult]:
        now_ts = time.time()
        results: List[DetectionResult] = []

        # Build bounding boxes from latest detections in tracks to consider occupancy
        track_bboxes = [t.detections[-1].bbox for t in tracks if t.detections]

        # Group detections by some stable id if provided, otherwise by proximity
        # For simplicity, examine detections of suspicious labels and check
        # whether they appear stationary across recent frames in 'detections'.
        candidates: Dict[Optional[str], List[Detection]] = {}
        for det in detections:
            if det.label not in self.suspicious_labels:
                continue
            if det.confidence < self.min_confidence:
                continue
            # skip if matched to a person/enclosing track (occupied)
            occupied = False
            for tb in track_bboxes:
                if iou(tb, det.bbox) >= self.match_track_iou:
                    occupied = True
                    break
            if occupied:
                continue
            # bucket by detection id when available
            key = det.id
            if key not in candidates:
                candidates[key] = []
            candidates[key].append(det)

        for key, dets in candidates.items():
            if len(dets) < 2:
                # not enough evidence yet; skip
                continue
            # sort by timestamp
            dets_sorted = sorted(dets, key=lambda d: d.timestamp)
            duration = dets_sorted[-1].timestamp - dets_sorted[0].timestamp
            if duration < self.min_duration_s:
                continue
            # check movement across the series
            centroids = [bbox_to_centroid(d.bbox) for d in dets_sorted]
            minx = min(c[0] for c in centroids)
            maxx = max(c[0] for c in centroids)
            miny = min(c[1] for c in centroids)
            maxy = max(c[1] for c in centroids)
            span = math.hypot(maxx - minx, maxy - miny)
            if span <= self.max_movement_px:
                last = dets_sorted[-1]
                results.append(
                    DetectionResult(
                        detector="suspicious_object",
                        detection_id=last.id,
                        track_id=None,
                        label=last.label,
                        score=float(last.confidence),
                        metadata={"duration_s": duration, "span_px": span},
                    )
                )
        return results


# Small convenience factory for typing and defaults -------------------------

__all__ = [
    "DetectorProtocol",
    "BaseEventDetector",
    "Detection",
    "Track",
    "DetectionResult",
    "RestrictedAreaDetector",
    "LineCrossingDetector",
    "LoiteringDetector",
    "SuspiciousObjectDetector",
]
