"""Lightweight tracker implementations with a pluggable ByteTrack wrapper and a
simple CentroidTracker fallback.

This module avoids heavy imports at import time. External tracker backends
(e.g. ByteTrack) are imported lazily inside the wrapper so that importing this
module does not raise heavy dependency errors.

Tracker API (TrackerProtocol):
- update(detections, frame_id=None) -> List[dict]
    Accepts a sequence of detections, each detection is expected to be a tuple
    or list in the form (x1, y1, x2, y2[, score]). Returns a list of tracked
    objects as dicts: {'id': int, 'bbox': (x1,y1,x2,y2), 'centroid':(cx,cy),
    'score': float | None}.
- reset() -> None

The ByteTrack wrapper will be used if a compatible BYTETracker class can be
imported at runtime. Otherwise a pure-Python CentroidTracker is used.
"""
from __future__ import annotations

import importlib
import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple, runtime_checkable

_logger = logging.getLogger(__name__)

BBox = Tuple[float, float, float, float]
Detection = Tuple[float, float, float, float, Optional[float]]
TrackDict = Dict[str, Any]


@runtime_checkable
class BaseTracker(Protocol):
    """Abstract protocol for vision object trackers used by the pipeline."""

    def update(self, detections: Sequence[Detection] | Sequence[dict], frame_id: Optional[int] = None) -> List[Track]:
        ...

    def reset(self) -> None:
        ...


TrackerProtocol = BaseTracker


@dataclass
class Track:
    """Typed track object representing a tracked object across video frames.

    Contains track_id, class_id, class_name, confidence, bounding_box,
    timestamp, camera_id, track_age, and track_duration.
    """

    track_id: int
    bbox: BBox
    centroid: Optional[Tuple[float, float]] = None
    score: Optional[float] = None
    class_id: Optional[int] = None
    class_name: str = "unknown"
    confidence: float = 0.0
    timestamp: float = 0.0
    camera_id: Optional[int] = None
    track_age: int = 1
    first_seen_ts: float = 0.0
    last_seen_ts: float = 0.0

    def __post_init__(self) -> None:
        if self.centroid is None:
            x1, y1, x2, y2 = self.bbox
            self.centroid = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        if self.score is not None and self.confidence == 0.0:
            self.confidence = float(self.score)
        elif self.confidence > 0.0 and self.score is None:
            self.score = self.confidence
        if self.first_seen_ts == 0.0 and self.timestamp > 0.0:
            self.first_seen_ts = self.timestamp
        if self.last_seen_ts == 0.0 and self.timestamp > 0.0:
            self.last_seen_ts = self.timestamp

    @property
    def track_duration(self) -> float:
        """Return total duration in seconds the track has been active."""
        if self.first_seen_ts > 0.0 and self.last_seen_ts >= self.first_seen_ts:
            return self.last_seen_ts - self.first_seen_ts
        return 0.0

    @property
    def bounding_box(self) -> BBox:
        return self.bbox

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return key in (
            "id",
            "track_id",
            "bbox",
            "bounding_box",
            "centroid",
            "score",
            "confidence",
            "class_id",
            "class_name",
            "timestamp",
            "camera_id",
            "track_age",
            "track_duration",
        )

    def __getitem__(self, key: str) -> object:
        if key in ("id", "track_id"):
            return self.track_id
        if key in ("bbox", "bounding_box"):
            return self.bbox
        if key == "centroid":
            return self.centroid
        if key in ("score", "confidence"):
            return self.confidence if self.confidence != 0.0 else self.score
        if key == "class_id":
            return self.class_id
        if key == "class_name":
            return self.class_name
        if key == "timestamp":
            return self.timestamp
        if key == "camera_id":
            return self.camera_id
        if key == "track_age":
            return self.track_age
        if key == "track_duration":
            return self.track_duration
        raise KeyError(key)

    def __iter__(self):
        for k in (
            "id",
            "track_id",
            "bbox",
            "bounding_box",
            "centroid",
            "score",
            "confidence",
            "class_id",
            "class_name",
            "timestamp",
            "camera_id",
            "track_age",
            "track_duration",
        ):
            yield k


class CentroidTracker:
    """A simple, dependency-free centroid tracker.

    Uses nearest-centroid matching with a disappearance counter. This is a
    straightforward fallback if a native ByteTrack implementation isn't
    importable.
    """

    def __init__(self, max_disappeared: int = 50, max_distance: float = 50.0) -> None:
        self._next_id = 1
        self._objects: Dict[int, Tuple[float, float]] = {}
        self._bboxes: Dict[int, BBox] = {}
        self._scores: Dict[int, Optional[float]] = {}
        self._class_ids: Dict[int, Optional[int]] = {}
        self._class_names: Dict[int, str] = {}
        self._disappeared: Dict[int, int] = {}
        self._max_disappeared = int(max_disappeared)
        self._max_distance = float(max_distance)

    def reset(self) -> None:
        self._next_id = 1
        self._objects.clear()
        self._bboxes.clear()
        self._scores.clear()
        self._class_ids.clear()
        self._class_names.clear()
        self._disappeared.clear()

    def _centroid_from_bbox(self, bbox: BBox) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def update(self, detections: Sequence[Detection] | Sequence[dict], frame_id: Optional[int] = None) -> List[Track]:
        rects: List[BBox] = []
        scores: List[Optional[float]] = []
        class_ids: List[Optional[int]] = []
        class_names: List[str] = []
        for det in detections:
                # Accept dicts of the form {'bbox': [x1,y1,x2,y2], 'score': ...} or sequences/tuples
                if isinstance(det, dict):
                    bbox = det.get('bbox') or det.get('box')
                    if bbox and len(bbox) >= 4:
                        x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                        rects.append((x1, y1, x2, y2))
                        # Safely coerce score to float when possible
                        score_raw = det.get('score')
                        try:
                            score_val: Optional[float] = float(score_raw) if score_raw is not None else None
                        except Exception:
                            score_val = None
                        scores.append(score_val)
                        class_id_raw = det.get('class_id')
                        try:
                            class_ids.append(int(class_id_raw) if class_id_raw is not None else None)
                        except Exception:
                            class_ids.append(None)
                        class_names.append(str(det.get('class_name') or 'unknown'))
                    continue
                # otherwise treat as sequence/tuple
                if len(det) >= 4:
                    x1, y1, x2, y2 = float(det[0]), float(det[1]), float(det[2]), float(det[3])
                    rects.append((x1, y1, x2, y2))
                    scores.append(float(det[4]) if len(det) > 4 and det[4] is not None else None)
                    class_ids.append(None)
                    class_names.append('unknown')

        if len(rects) == 0:
            # No detections: increment disappeared counters and remove long-gone objects
            ids_to_remove = []
            for oid in list(self._disappeared.keys()):
                self._disappeared[oid] += 1
                if self._disappeared[oid] > self._max_disappeared:
                    ids_to_remove.append(oid)
            for oid in ids_to_remove:
                self._objects.pop(oid, None)
                self._bboxes.pop(oid, None)
                self._scores.pop(oid, None)
                self._class_ids.pop(oid, None)
                self._class_names.pop(oid, None)
                self._disappeared.pop(oid, None)
            return self._format_tracks()

        input_centroids = [self._centroid_from_bbox(b) for b in rects]

        if len(self._objects) == 0:
            for i, c in enumerate(input_centroids):
                oid = self._next_id
                self._next_id += 1
                self._objects[oid] = c
                self._bboxes[oid] = rects[i]
                self._scores[oid] = scores[i]
                self._class_ids[oid] = class_ids[i]
                self._class_names[oid] = class_names[i]
                self._disappeared[oid] = 0
            return self._format_tracks()

        # Build distance matrix between existing objects and input centroids
        object_ids = list(self._objects.keys())
        object_centroids = [self._objects[oid] for oid in object_ids]

        distances: List[List[float]] = []
        for oc in object_centroids:
            row: List[float] = []
            for ic in input_centroids:
                dx = oc[0] - ic[0]
                dy = oc[1] - ic[1]
                row.append(math.hypot(dx, dy))
            distances.append(row)

        # Greedy assignment: for small numbers this is fine and avoids heavier deps
        assigned_objs: Dict[int, int] = {}  # object_idx -> detection_idx
        assigned_dets: Dict[int, int] = {}

        # Flatten pairs and sort by distance
        pairs: List[Tuple[float, int, int]] = []
        for oi, row in enumerate(distances):
            for di, d in enumerate(row):
                pairs.append((d, oi, di))
        pairs.sort(key=lambda x: x[0])

        for d, oi, di in pairs:
            if oi in assigned_objs or di in assigned_dets:
                continue
            if d > self._max_distance:
                continue
            assigned_objs[oi] = di
            assigned_dets[di] = oi

        # Update matched objects
        matched_obj_ids = set()
        for oi, di in assigned_objs.items():
            oid = object_ids[oi]
            self._objects[oid] = input_centroids[di]
            self._bboxes[oid] = rects[di]
            self._scores[oid] = scores[di]
            self._class_ids[oid] = class_ids[di]
            self._class_names[oid] = class_names[di]
            self._disappeared[oid] = 0
            matched_obj_ids.add(oid)

        # Mark unmatched existing objects as disappeared
        for oid in object_ids:
            if oid not in matched_obj_ids:
                self._disappeared[oid] = self._disappeared.get(oid, 0) + 1
                if self._disappeared[oid] > self._max_disappeared:
                    self._objects.pop(oid, None)
                    self._bboxes.pop(oid, None)
                    self._scores.pop(oid, None)
                    self._class_ids.pop(oid, None)
                    self._class_names.pop(oid, None)
                    self._disappeared.pop(oid, None)

        # Register unmatched detections as new objects
        for di in range(len(input_centroids)):
            if di not in assigned_dets:
                oid = self._next_id
                self._next_id += 1
                self._objects[oid] = input_centroids[di]
                self._bboxes[oid] = rects[di]
                self._scores[oid] = scores[di]
                self._class_ids[oid] = class_ids[di]
                self._class_names[oid] = class_names[di]
                self._disappeared[oid] = 0

        return self._format_tracks()

    def _format_tracks(self) -> List[Track]:
        out: List[Track] = []
        for oid, centroid in self._objects.items():
            b = self._bboxes.get(oid, (0.0, 0.0, 0.0, 0.0))
            try:
                x1, y1, x2, y2 = b  # ensure exact tuple length
                bbox: BBox = (float(x1), float(y1), float(x2), float(y2))
            except Exception:
                bbox = (0.0, 0.0, 0.0, 0.0)
            out.append(Track(
                track_id=int(oid),
                bbox=bbox,
                centroid=(float(centroid[0]), float(centroid[1])),
                score=self._scores.get(oid),
                class_id=self._class_ids.get(oid),
                class_name=self._class_names.get(oid, "unknown"),
            ))
        return out


class ByteTrackWrapper:
    """A thin, lazy wrapper around an available BYTETracker implementation.

    The wrapper attempts to import a BYTETracker class from a few common module
    paths at runtime. If the import or construction fails, it falls back to an
    internal CentroidTracker to maintain functionality without raising import
    errors.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Do not import heavy modules at the top level. Try now, but be robust.
        self._backend: Optional[Any] = None
        self._fallback = CentroidTracker(max_disappeared=kwargs.pop('max_disappeared', 50),
                                         max_distance=kwargs.pop('max_distance', 50.0))

        tracker_cls = self._find_bytrack_class()
        if tracker_cls is None:
            _logger.debug("BYTETracker not found; using CentroidTracker fallback")
            return

        # Try to instantiate the backend with a few sensible defaults. Some
        # BYTETracker implementations accept different parameters; try a
        # no-arg constructor first, then a small defaults set.
        try:
            try:
                self._backend = tracker_cls(*args, **kwargs)
            except Exception:
                defaults = dict(track_thresh=0.5, track_buffer=30, match_thresh=0.8, frame_rate=30)
                merged = {**defaults, **kwargs}
                self._backend = tracker_cls(**merged)
        except Exception as exc:  # pragma: no cover - defensive
            _logger.exception("Failed to instantiate BYTETracker backend, falling back: %s", exc)
            self._backend = None

    def reset(self) -> None:
        if self._backend is None:
            self._fallback.reset()
            return
        # Delegate if backend provides reset
        if hasattr(self._backend, 'reset'):
            try:
                self._backend.reset()
            except Exception:
                _logger.debug("Backend reset failed; clearing fallback")
                self._fallback.reset()
        else:
            # No reset on backend; clear fallback for safety
            self._fallback.reset()

    def update(self, detections: Sequence[Detection] | Sequence[dict], frame_id: Optional[int] = None) -> List[Track]:
        # If no backend, use fallback
        if self._backend is None:
            return self._fallback.update(detections, frame_id=frame_id)

        # Attempt to adapt incoming detections to backend expected format.
        # Common ByteTrack backends expect numpy arrays of [x, y, w, h, score].
        try:
            import numpy as _np  # local import only when needed

            dets_for_backend = []
            for det in detections:
                x1, y1, x2, y2 = float(det[0]), float(det[1]), float(det[2]), float(det[3])
                w = x2 - x1
                h = y2 - y1
                score = float(det[4]) if len(det) > 4 and det[4] is not None else 0.0
                dets_for_backend.append([x1, y1, w, h, score])

            np_dets = _np.asarray(dets_for_backend, dtype=_np.float32) if dets_for_backend else _np.empty((0, 5), dtype=_np.float32)

            # Common update signatures:
            # - update(dets, img_info) or update(dets, frame_id=...)
            result = None
            if hasattr(self._backend, 'update'):
                try:
                    # Try common two-arg signature
                    result = self._backend.update(np_dets, frame_id)
                except TypeError:
                    try:
                        # Try keyword frame_id
                        result = self._backend.update(np_dets, frame_id=frame_id)
                    except Exception:
                        result = self._backend.update(np_dets)
            else:
                # No update method - fallback
                return self._fallback.update(detections, frame_id=frame_id)

            # Normalize backend result to list of Track objects
            return self._normalize_backend_result(result)

        except Exception as exc:  # pragma: no cover - defensive
            _logger.exception("BYTETracker backend update failed, falling back: %s", exc)
            return self._fallback.update(detections, frame_id=frame_id)

    def _normalize_backend_result(self, result: Any) -> List[Track]:
        """Attempt to convert backend-specific results into a list of Track
        objects. This is defensive: support tuples, sequences, and objects from
        various backend implementations.
        """
        out: List[Track] = []
        if result is None:
            return out

        # If backend returned an iterable of tracks
        try:
            for item in result:
                # Support tuple/list like (track_id, x1, y1, x2, y2, score)
                if isinstance(item, (list, tuple)):
                    if len(item) >= 6:
                        tid = int(item[0])
                        bbox = (float(item[1]), float(item[2]), float(item[3]), float(item[4]))
                        score = float(item[5])
                        cx = (bbox[0] + bbox[2]) / 2.0
                        cy = (bbox[1] + bbox[3]) / 2.0
                        out.append(Track(track_id=int(tid), bbox=bbox, centroid=(cx, cy), score=score))
                        continue
                    # Some implementations return [x,y,w,h,track_id]
                    if len(item) == 5:
                        # guess: [x,y,w,h,id]
                        x, y, w, h, tid = item
                        bbox = (float(x), float(y), float(x + w), float(y + h))
                        cx = (bbox[0] + bbox[2]) / 2.0
                        cy = (bbox[1] + bbox[3]) / 2.0
                        out.append(Track(track_id=int(tid), bbox=bbox, centroid=(cx, cy), score=None))
                        continue

                # If item is an object with attributes
                track_id_obj: Optional[int] = None
                raw_tid = getattr(item, 'track_id', None) or getattr(item, 'tid', None) or getattr(item, 'id', None)
                if raw_tid is not None:
                    try:
                        track_id_obj = int(raw_tid)
                    except Exception:
                        track_id_obj = None
                bbox_obj: Optional[Tuple[float, float, float, float]] = None
                if hasattr(item, 'tlbr'):
                    tlbr = getattr(item, 'tlbr')
                    try:
                        bbox_obj = (float(tlbr[0]), float(tlbr[1]), float(tlbr[2]), float(tlbr[3]))
                    except Exception:
                        bbox_obj = None
                if bbox_obj is None and hasattr(item, 'tlwh'):
                    tlwh = getattr(item, 'tlwh')
                    try:
                        x, y, w, h = tlwh
                        bbox_obj = (float(x), float(y), float(x + w), float(y + h))
                    except Exception:
                        bbox_obj = None

                if track_id_obj is not None and bbox_obj is not None:
                    cx = (bbox_obj[0] + bbox_obj[2]) / 2.0
                    cy = (bbox_obj[1] + bbox_obj[3]) / 2.0
                    score_raw = getattr(item, 'score', None)
                    try:
                        score_val = float(score_raw) if score_raw is not None else None
                    except Exception:
                        score_val = None
                    out.append(Track(track_id=int(track_id_obj), bbox=bbox_obj, centroid=(cx, cy), score=score_val))
                    continue

                # Last resort: try to interpret as a sequence of numbers
                try:
                    seq = list(item)
                    if len(seq) >= 6:
                        tid = int(seq[0])
                        bbox = (float(seq[1]), float(seq[2]), float(seq[3]), float(seq[4]))
                        score = float(seq[5])
                        cx = (bbox[0] + bbox[2]) / 2.0
                        cy = (bbox[1] + bbox[3]) / 2.0
                        out.append(Track(track_id=int(tid), bbox=bbox, centroid=(cx, cy), score=score))
                        continue
                except Exception:
                    pass

            return out
        except TypeError:
            # Not iterable - try to handle single object
            pass

        # If result is a single track-like object
        try:
            item = result
            track_id_single: Optional[int] = None
            raw_tid = getattr(item, 'track_id', None) or getattr(item, 'tid', None) or getattr(item, 'id', None)
            if raw_tid is not None:
                try:
                    track_id_single = int(raw_tid)
                except Exception:
                    track_id_single = None
            if hasattr(item, 'tlbr'):
                tlbr = getattr(item, 'tlbr')
                bbox_single = (float(tlbr[0]), float(tlbr[1]), float(tlbr[2]), float(tlbr[3]))
                cx = (bbox_single[0] + bbox_single[2]) / 2.0
                cy = (bbox_single[1] + bbox_single[3]) / 2.0
                score_raw = getattr(item, 'score', None)
                try:
                    score_val = float(score_raw) if score_raw is not None else None
                except Exception:
                    score_val = None
                if track_id_single is not None:
                    return [Track(track_id=int(track_id_single), bbox=bbox_single, centroid=(cx, cy), score=score_val)]
        except Exception:
            pass

        return out

    @staticmethod
    def _find_bytrack_class() -> Optional[Any]:
        """Try several common module paths for ByteTrack's BYTETracker class.

        This is a best-effort search; it's intentionally permissive so that the
        presence of a ByteTrack backend can be detected without importing heavy
        modules at import time.
        """
        candidates = (
            'bytetrack',
            'bytetrack.byte_tracker',
            'bytetrack.tracker',
            'yolox.tracker.byte_tracker',
            'byte_track',
        )
        for mod_name in candidates:
            try:
                mod = importlib.import_module(mod_name)
                for attr in ('BYTETracker', 'ByteTrack', 'ByteTracker'):
                    cls = getattr(mod, attr, None)
                    if cls is not None:
                        _logger.debug('Found BYTETracker class in %s.%s', mod_name, attr)
                        return cls
            except Exception:
                continue
        return None


class ByteTrackTracker(ByteTrackWrapper):
    """ByteTrack tracker adapter implementing BaseTracker interface."""

    def __init__(
        self,
        track_thresh: float = 0.5,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        frame_rate: int = 30,
        max_disappeared: int = 50,
        max_distance: float = 50.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            track_thresh=track_thresh,
            track_buffer=track_buffer,
            match_thresh=match_thresh,
            frame_rate=frame_rate,
            max_disappeared=max_disappeared,
            max_distance=max_distance,
            **kwargs,
        )


def create_tracker(use_byte: bool = True, **kwargs: Any) -> BaseTracker:
    """Factory that returns a tracker implementing BaseTracker interface.

    If use_byte is True, the function will try to create a ByteTrack-backed
    tracker; if that is not possible, it will return a CentroidTracker fallback.
    Additional kwargs are passed to the underlying constructors.
    """
    if use_byte:
        return ByteTrackTracker(**kwargs)

    return CentroidTracker(**kwargs)


__all__ = [
    'BaseTracker',
    'TrackerProtocol',
    'create_tracker',
    'CentroidTracker',
    'ByteTrackWrapper',
    'ByteTrackTracker',
    'Track',
]
