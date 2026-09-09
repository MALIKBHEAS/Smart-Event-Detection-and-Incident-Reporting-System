"""
RTSP / camera detection worker.

Implements RTSPDetectionWorker which reads frames from RTSP/USB/local files using
OpenCV in a background thread, processes frames asynchronously with a detector
(e.g. YOLODetector), uses a centroid tracker to detect new objects and creates
Event records in the DB while saving evidence images.

The implementation is intended to be modular and testable.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple


def resolve_device(device: Optional[str] = None) -> str:
    """Resolve device string to GPU (cuda) if available, falling back to CPU."""
    if device and device.lower() not in ("auto", "none"):
        return device
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


@dataclass
class WorkerConfig:
    source: Any
    camera_id: int
    camera_name: str
    detector_name: Optional[str] = None
    fps: float = 5.0
    confidence_threshold: float = 0.5
    frame_skip: int = 0
    device: Optional[str] = None
    event_detectors: list[dict[str, Any]] = field(default_factory=list)


try:
    import av
except ImportError:
    av = None

try:
    from app.plugins.audio.yamnet_detector import YAMNetDetector
except ImportError:
    YAMNetDetector = None

try:
    import cv2
except Exception as exc:  # pragma: no cover - environment dependent
    raise ImportError("OpenCV (cv2) is required by RTSPDetectionWorker") from exc

# Attempts to import YOLODetector; if missing raise informative error later when used
YOLODetector: Any = None
try:
    from app.plugins.cv.yolo_detector import YOLODetector
except Exception:  # do not raise here; construct will surface helpful message
    YOLODetector = None

# Try to import CentroidTracker; if not available provide a small fallback implementation
try:
    from app.plugins.cv.centroid_tracker import CentroidTracker as PluginCentroidTracker
except Exception:  # provide fallback
    PluginCentroidTracker = None

if PluginCentroidTracker is not None:
    CentroidTracker = PluginCentroidTracker
else:
    class FallbackCentroidTracker:
        """Simple centroid tracker fallback.

        Tracks objects by computing centroids of bounding boxes and assigning
        incremental IDs. Not production-grade but suitable as a fallback for tests.
        """

        def __init__(self, max_disappeared: int = 50) -> None:
            self.next_object_id = 0
            self.objects: Dict[int, Tuple[int, int]] = {}
            self.disappeared: Dict[int, int] = {}
            self.max_disappeared = max_disappeared

        def _centroid(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
            x, y, w, h = bbox
            return (int(x + w / 2), int(y + h / 2))

        def update(self, rects: List[Tuple[int, int, int, int]]) -> Dict[int, Tuple[int, int, int, int]]:
            """Update tracked objects from a list of bounding boxes.

            Returns mapping object_id -> bbox
            """
            if len(rects) == 0:
                # mark all disappeared
                for obj_id in list(self.disappeared.keys()):
                    self.disappeared[obj_id] = self.disappeared.get(obj_id, 0) + 1
                    if self.disappeared[obj_id] > self.max_disappeared:
                        self.objects.pop(obj_id, None)
                        self.disappeared.pop(obj_id, None)
                return {oid: (0, 0, 0, 0) for oid in self.objects.keys()}

            input_centroids = [self._centroid(r) for r in rects]

            if len(self.objects) == 0:
                for i, c in enumerate(input_centroids):
                    self.objects[self.next_object_id] = c
                    self.disappeared[self.next_object_id] = 0
                    self.next_object_id += 1
                return {oid: rects[i] for oid, i in zip(range(self.next_object_id - len(rects), self.next_object_id), range(len(rects)))}

            # Naive assignment: match by nearest centroid
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            assigned = {}
            used_inputs = set()
            for oid, ocent in zip(object_ids, object_centroids):
                # find closest input
                best_i = None
                best_dist = None
                for i, icent in enumerate(input_centroids):
                    if i in used_inputs:
                        continue
                    d = (ocent[0] - icent[0]) ** 2 + (ocent[1] - icent[1]) ** 2
                    if best_dist is None or d < best_dist:
                        best_dist = d
                        best_i = i
                if best_i is None:
                    self.disappeared[oid] = self.disappeared.get(oid, 0) + 1
                    if self.disappeared[oid] > self.max_disappeared:
                        self.objects.pop(oid, None)
                        self.disappeared.pop(oid, None)
                    continue
                # assign
                used_inputs.add(best_i)
                self.objects[oid] = input_centroids[best_i]
                self.disappeared[oid] = 0
                assigned[oid] = rects[best_i]

            # register unmatched inputs as new objects
            for i, rect in enumerate(rects):
                if i in used_inputs:
                    continue
                oid = self.next_object_id
                self.objects[oid] = input_centroids[i]
                self.disappeared[oid] = 0
                assigned[oid] = rect
                self.next_object_id += 1

            # assigned contains mapping; return mapping
            return assigned

    CentroidTracker = FallbackCentroidTracker

# detectors module requested by the user

detectors_module: ModuleType | None = None
try:
    from app.workers import detectors as detectors_module
except Exception:
    detectors_module = None

from app.db.session import SessionLocal
from app.domain.detection import RawDetection
from app.domain.event import EventData, EventSeverity
from app.notifications.manager import connection_manager
from app.notifications.repository import NotificationRepository
from app.services.detection_service import DetectionService
from app.services.event_detector_service import EventDetectorService
from app.services.event_fusion_service import EventFusionService
from app.workers.pipeline.context import FrameContext
from app.workers.pipeline.cv_detector_registry import default_detector, get_detector
from app.workers.pipeline.frame_processor import DetectionFrameProcessor

logger = logging.getLogger(__name__)


class RTSPDetectionWorker:
    """Async detection worker for a single camera/source.

    Reads frames from an OpenCV VideoCapture running in a background thread,
    processes frames with a detector and a centroid tracker, and creates Event
    DB records on new detections while saving evidence images.

    Public methods:
    - start() -> start background reading and processing
    - stop() -> stop the worker gracefully
    - restart() -> restart connection and processing
    - health_check() -> return status summary
    """

    def __init__(
        self,
        config: WorkerConfig,
        tracker: Optional[object] = None,
        fusion_service: EventFusionService | None = None,
    ) -> None:
        """Create a worker from a configuration object and an optional tracker."""
        self.config = config
        self.camera_id = config.camera_id
        self.camera_name = config.camera_name
        self.source = config.source
        self.detector_name = config.detector_name
        self.fps = float(config.fps)
        self.confidence_threshold = float(config.confidence_threshold)
        self.frame_skip = int(config.frame_skip)
        self.device = resolve_device(config.device)
        self._fusion_service = fusion_service or EventFusionService()
        self._event_detector_service = EventDetectorService(config.event_detectors or [])

        self._cap: Optional["cv2.VideoCapture"] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._reader_stop = threading.Event()
        self._frame_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._processing_task: Optional[asyncio.Task] = None
        self._connected = False
        self._last_frame_ts: Optional[float] = None
        self._latest_frame: Optional[Any] = None  # for MJPEG streaming; raw BGR frame, no overlays
        self._latest_tracked_objects: List[Any] = []  # rich Track objects (bbox/class_name/confidence/track_id) for stream overlays
        self._tracker = tracker if tracker is not None else CentroidTracker()
        self._detector: Optional[object] = None
        self._stop_requested = False

        self._audio_detector = None
        if getattr(YAMNetDetector, "__name__", None) is not None and av is not None:
            self._audio_detector = YAMNetDetector()
        self._audio_thread = None

        # reconnection/backoff
        self._backoff_initial = 1.0
        self._backoff_max = 30.0

        # prepare evidence directory
        base_app_dir = Path(__file__).resolve().parent.parent
        self.evidence_root = base_app_dir / "evidence"
        self.evidence_root.mkdir(parents=True, exist_ok=True)

        # configure detector now if possible
        self._setup_detector()
        self._detection_service = DetectionService(self._detector)
        self._frame_processor = DetectionFrameProcessor(
            self._detection_service,
            self._event_detector_service,
            self._tracker,
            confidence_threshold=self.confidence_threshold,
        )

    def _setup_detector(self) -> None:
        """Set up detector instance according to availability and configuration.

        Resolution order:
        1. Legacy ``app.workers.detectors.get_detector`` when configured by name
        2. Pipeline CV registry (``get_detector`` / ``default_detector``)
        3. Direct YOLODetector fallback for backward compatibility
        """
        kwargs: Dict[str, Any] = {}
        if self.device is not None:
            kwargs["device"] = self.device

        if detectors_module is not None and self.detector_name:
            factory = getattr(detectors_module, "get_detector", None)
            if callable(factory):
                try:
                    self._detector = factory(self.detector_name, **kwargs)
                    logger.debug("Using detector from detectors_module: %s", self.detector_name)
                    return
                except Exception as exc:
                    logger.exception(
                        "Failed to initialize detector '%s' from workers.detectors: %s",
                        self.detector_name,
                        exc,
                    )

        if self.detector_name:
            try:
                self._detector = get_detector(self.detector_name, **kwargs)
                logger.debug("Using CV registry detector: %s", self.detector_name)
                return
            except ValueError:
                logger.warning("Unknown detector '%s'; falling back to default detector", self.detector_name)
            except Exception as exc:
                logger.exception("Failed to initialize CV registry detector '%s': %s", self.detector_name, exc)

        if self.detector_name is None:
            try:
                self._detector = default_detector(**kwargs)
                logger.debug("Initialized default CV detector for worker %s", self.camera_name)
                return
            except Exception as exc:
                logger.exception("Failed to initialize default CV detector: %s", exc)

        if detectors_module is not None and hasattr(detectors_module, "default_detector"):
            try:
                self._detector = detectors_module.default_detector(**kwargs)
                return
            except Exception as exc:
                logger.exception("Failed to initialize default detector from detectors_module: %s", exc)

        if YOLODetector is not None:
            try:
                self._detector = YOLODetector(**kwargs)
                logger.debug("Initialized YOLODetector fallback for worker %s", self.camera_name)
                return
            except Exception as exc:
                logger.exception("Failed to initialize YOLODetector fallback: %s", exc)

        self._detector = default_detector(**kwargs)

    async def start(self) -> None:
        """Start reader thread and processing coroutine. Call from running event loop."""
        if self._stop_requested:
            self._stop_requested = False

        self._audio_detector = None
        if getattr(YAMNetDetector, "__name__", None) is not None and av is not None:
            self._audio_detector = YAMNetDetector()
        self._audio_thread = None

        if self._processing_task and not self._processing_task.done():
            logger.info("Worker %s already started", self.camera_name)
            return

        self._loop = asyncio.get_running_loop()
        self._frame_queue = asyncio.Queue(maxsize=8)
        self._reader_stop.clear()

        # Start background reader thread
        self._reader_thread = threading.Thread(target=self._reader_loop, name=f"reader-{self.camera_name}", daemon=True)
        self._reader_thread.start()

        # Start processing task (which will also ensure capture is connected if reader drops)
        self._processing_task = self._loop.create_task(self._processing_loop())
        
        # Ensure capture asynchronously to avoid blocking the caller (like API endpoints)
        self._loop.create_task(self._initial_connect())
        
        if getattr(self, '_audio_detector', None) is not None:
            self._audio_thread = threading.Thread(target=self._audio_reader_loop, name=f"audio-{self.camera_name}", daemon=True)
            self._audio_thread.start()
        logger.info("Started RTSPDetectionWorker for %s", self.camera_name)
        
    async def _initial_connect(self) -> None:
        """Background task to initially connect the camera."""
        try:
            await self._ensure_capture()
        except Exception as e:
            logger.error("Initial connect failed for camera %s: %s", self.camera_name, e)

    async def stop(self) -> None:
        """Stop processing and reader thread gracefully."""
        self._stop_requested = True
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

        # stop reader thread
        self._reader_stop.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)
            
        if getattr(self, '_audio_thread', None) and self._audio_thread.is_alive():
            self._audio_thread.join(timeout=2.0)
            self._reader_thread = None

        # release capture
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                logger.exception("Error releasing capture for %s", self.camera_name)
            self._cap = None

        self._set_connected(False)
        logger.info("Stopped RTSPDetectionWorker for %s", self.camera_name)

    async def restart(self) -> None:
        """Restart the worker by stopping then starting again."""
        await self.stop()
        await self.start()

    def health_check(self) -> Dict[str, Any]:
        """Return a small dict describing worker health."""
        return {
            "camera_name": self.camera_name,
            "connected": self._connected,
            "last_frame_timestamp": self._last_frame_ts,
            "queue_size": self._frame_queue.qsize() if self._frame_queue is not None else None,
        }

    def _set_connected(self, value: bool) -> None:
        """Update connection state, firing a notification+broadcast only on
        an actual transition (not on every poll/read) -- avoids spamming
        operators. Safe to call from either the asyncio loop or the
        background reader thread."""
        if self._connected == value:
            return
        self._connected = value
        try:
            session = SessionLocal()
            try:
                kind = "camera_online" if value else "camera_offline"
                message = f"{self.camera_name} is now {'online' if value else 'offline'}"
                record = NotificationRepository(session).create(
                    type=kind,
                    message=message,
                    severity="low" if value else "medium",
                    related_type="camera",
                    related_id=self.camera_id,
                )
                connection_manager.broadcast_threadsafe(
                    {
                        "id": record.id,
                        "type": record.type,
                        "message": record.message,
                        "severity": record.severity,
                        "related_type": record.related_type,
                        "related_id": record.related_id,
                    }
                )
            finally:
                session.close()
        except Exception:
            logger.exception("Failed to create/broadcast connection-state notification for %s", self.camera_name)

    def _open_capture(self) -> "cv2.VideoCapture":
        src = self.source
        if isinstance(src, str) and src.isdigit():
            src = int(src)
        return cv2.VideoCapture(src)

    async def _ensure_capture(self) -> None:
        """Ensure cv2.VideoCapture is opened; reconnect with exponential backoff on failure."""
        backoff = self._backoff_initial
        while not self._stop_requested:
            try:
                if self._cap is not None:
                    try:
                        # quick check
                        if self._cap.isOpened():
                            self._set_connected(True)
                            return
                    except Exception:
                        pass

                def _open_and_warmup():
                    cap = self._open_capture()
                    ok, _ = cap.read()
                    if not ok:
                        cap.release()
                        raise RuntimeError("VideoCapture failed initial read")
                    return cap

                # create capture in a background thread to prevent blocking the async event loop
                self._cap = await asyncio.to_thread(_open_and_warmup)

                self._set_connected(True)
                logger.info("Connected to source %s for camera %s", self.source, self.camera_name)
                return
            except Exception as exc:
                logger.warning("Failed to open capture for %s: %s. Reconnecting in %.1fs", self.camera_name, exc, backoff)
                if getattr(self, '_cap', None) is not None:
                    try:
                        self._cap.release()
                    except Exception:
                        pass
                    self._cap = None
                self._set_connected(False)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._backoff_max)

        raise RuntimeError("Stop requested while attempting to open capture")

    def _reader_loop(self) -> None:
        """Background thread that reads frames and pushes them into the asyncio queue."""
        assert self._loop is not None and self._frame_queue is not None
        logger.debug("Reader thread started for %s", self.camera_name)
        while not self._reader_stop.is_set() and not self._stop_requested:
            if self._cap is None:
                # attempt to re-open synchronously (best effort)
                try:
                    self._cap = self._open_capture()
                except Exception:
                    logger.exception("Reader failed to create VideoCapture for %s", self.camera_name)
                    time.sleep(1.0)
                    continue

            try:
                ok, frame = self._cap.read()
                ts = time.time()
                if not ok or frame is None:
                    # mark disconnected and attempt quick reconnect
                    self._set_connected(False)
                    logger.debug("Reader failed to read frame for %s", self.camera_name)
                    if self._cap is not None:
                        try:
                            self._cap.release()
                        except Exception:
                            pass
                        self._cap = None
                    time.sleep(0.5)
                    continue

                # update last frame time
                self._last_frame_ts = ts
                self._latest_frame = frame

                # put frame into asyncio queue (drop frame if full)
                try:
                    fut = asyncio.run_coroutine_threadsafe(self._frame_queue.put((ts, frame)), self._loop)
                    fut.result(timeout=1.0)
                except Exception:
                    # queue probably full or loop gone; drop frame
                    logger.debug("Dropping frame for %s (queue full or loop closed)", self.camera_name)

            except Exception:
                logger.exception("Exception in reader loop for %s", self.camera_name)
                time.sleep(0.2)

        logger.debug("Reader thread exiting for %s", self.camera_name)

    async def _processing_loop(self) -> None:
        """Async loop that processes frames at the configured FPS and handles detections."""
        assert self._frame_queue is not None
        interval = 1.0 / max(0.0001, self.fps)
        frames_processed = 0
        try:
            while not self._stop_requested:
                start = time.time()
                try:
                    ts, frame = await asyncio.wait_for(self._frame_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # check connection health
                    if not self._connected:
                        # attempt to re-open if connection lost
                        try:
                            await self._ensure_capture()
                        except Exception:
                            # will be retried by ensure_capture
                            pass
                    await asyncio.sleep(0.1)
                    continue

                # frame skipping
                if self.frame_skip and (frames_processed % (self.frame_skip + 1) != 0):
                    frames_processed += 1
                    continue

                try:
                    processed = self._frame_processor.process(
                        FrameContext(
                            timestamp=ts,
                            frame=frame,
                            camera_id=self.camera_id,
                            camera_name=self.camera_name,
                        )
                    )
                except Exception:
                    logger.exception("Frame processor failed for %s", self.camera_name)
                    processed = None

                if processed is not None:
                    self._latest_tracked_objects = processed.tracked_objects

                if processed and processed.filtered_detections:
                    await self._handle_processed_frame(processed)

                frames_processed += 1

                elapsed = time.time() - start
                sleep_for = max(0.0, interval - elapsed)
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
        except asyncio.CancelledError:
            logger.debug("Processing loop cancelled for %s", self.camera_name)
        except Exception:
            logger.exception("Unexpected exception in processing loop for %s", self.camera_name)

    def _run_detector(self, frame) -> List[RawDetection]:
        """Run detector on the provided frame and return list of raw detections."""
        if self._detection_service is None:
            raise RuntimeError("Detection service is not initialized")

        try:
            return self._detection_service.detect(frame, confidence_threshold=self.confidence_threshold)
        except Exception:
            logger.exception("Error while running detector for %s", self.camera_name)
            return []

    async def _handle_detections(self, ts: float, frame, detections: List[RawDetection]) -> None:
        """Backward-compatible wrapper that delegates to the frame processor."""
        context = FrameContext(
            timestamp=ts,
            frame=frame,
            camera_id=self.camera_id,
            camera_name=self.camera_name,
        )
        processed = self._frame_processor.process_detections(context, detections)
        await self._handle_processed_frame(processed)

    async def _handle_processed_frame(self, processed) -> None:
        """Persist evidence and ingest fused events from a processed frame."""
        screenshot_path: Optional[Path] = None
        try:
            screenshot_path = self._save_screenshot(processed.frame, processed.timestamp)
        except Exception:
            logger.exception("Failed saving screenshot for %s", self.camera_name)

        for event in processed.events:
            payload: Dict[str, Any] = {
                "camera": self.camera_name,
                "event_detector": event.detector,
                "track_id": event.track_id,
                "metadata": event.metadata,
            }
            if screenshot_path:
                payload["screenshot_path"] = str(screenshot_path)

            event_data = EventData(
                camera_id=self.camera_id,
                camera_name=self.camera_name,
                event_type=event.detector,
                severity=EventSeverity.from_score(float(event.score)),
                score=float(event.score),
                timestamp=datetime.datetime.utcfromtimestamp(processed.timestamp),
                payload=payload,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
            )

            try:
                event_id = await asyncio.to_thread(self._fusion_service.ingest, event_data)
                logger.info(
                    "Event fused and ingested for camera=%s track=%s detector=%s",
                    self.camera_name,
                    event.track_id,
                    event.detector,
                )
                if event_id is not None:
                    await self._notify_new_event(event_id, event_data)
            except Exception:
                logger.exception("Failed ingesting fused event for %s", self.camera_name)

    async def _notify_new_event(self, event_id: int, event_data) -> None:
        # Only medium+ severity to avoid flooding the notification panel
        # with every low-confidence detection.
        if event_data.severity.value == "low":
            return
        try:
            from app.db.session import SessionLocal
            from app.notifications.manager import connection_manager
            from app.notifications.repository import NotificationRepository
            from app.repositories.settings_repository import SettingsRepository

            def _persist():
                session = SessionLocal()
                try:
                    if not SettingsRepository(session).get().notify_on_new_event:
                        return None
                    repo = NotificationRepository(session)
                    return repo.create(
                        type="new_event",
                        message=f"{event_data.event_type.replace('_', ' ').title()} detected on {event_data.camera_name}",
                        severity=event_data.severity.value,
                        related_type="event",
                        related_id=event_id,
                    )
                finally:
                    session.close()

            record = await asyncio.to_thread(_persist)
            if record is None:
                return
            await connection_manager.broadcast(
                {
                    "id": record.id,
                    "type": record.type,
                    "message": record.message,
                    "severity": record.severity,
                    "related_type": record.related_type,
                    "related_id": record.related_id,
                    "read": False,
                }
            )
        except Exception:
            logger.exception("Failed to broadcast new-event notification for %s", self.camera_name)

    def _save_screenshot(self, frame, ts: float) -> Optional[Path]:
        """Save screenshot JPEG to evidence directory and return Path."""
        try:
            ts_str = datetime.datetime.utcfromtimestamp(ts).strftime("%Y%m%dT%H%M%SZ")
            cam_dir = self.evidence_root / self.camera_name
            cam_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{ts_str}.jpg"
            path = cam_dir / filename
            # OpenCV expects BGR; ensure frame is an array
            cv2.imwrite(str(path), frame)
            return path
        except Exception:
            logger.exception("Failed to write screenshot for %s", self.camera_name)
            return None


    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<RTSPDetectionWorker camera={self.camera_name} source={self.source}>"

    def _audio_reader_loop(self) -> None:
        if av is None or getattr(self, '_audio_detector', None) is None:
            return
            
        import numpy as np
        from collections import defaultdict
        import datetime
        
        audio_history = defaultdict(list)
        
        while not self._reader_stop.is_set() and not getattr(self, '_stop_requested', False):
            container = None
            try:
                container = av.open(self.source, timeout=5000000, options={'rtsp_transport': 'tcp'})
                audio_stream = None
                for stream in container.streams:
                    if stream.type == 'audio':
                        audio_stream = stream
                        break
                        
                if audio_stream is None:
                    container.close()
                    for _ in range(30):
                        if self._reader_stop.is_set() or getattr(self, '_stop_requested', False): break
                        time.sleep(1)
                    continue

                resampler = av.audio.resampler.AudioResampler(format='s16', layout='mono', rate=16000)
                audio_buffer = []
                TARGET_SAMPLES = 15600
                
                for frame in container.decode(audio_stream):
                    if self._reader_stop.is_set() or getattr(self, '_stop_requested', False):
                        break
                        
                    resampled_frames = resampler.resample(frame)
                    for r_frame in resampled_frames:
                        arr = r_frame.to_ndarray()
                        arr_float = arr.astype(np.float32) / 32768.0
                        audio_buffer.extend(arr_float[0].tolist())
                        
                    while len(audio_buffer) >= TARGET_SAMPLES:
                        chunk = audio_buffer[:TARGET_SAMPLES]
                        audio_buffer = audio_buffer[TARGET_SAMPLES:]
                        
                        detections = self._audio_detector.detect(np.array(chunk))
                        for det in detections:
                            class_name = det['class_name']
                            score = det['confidence']
                            now_ts = det['timestamp']
                            
                            audio_history[class_name].append(now_ts)
                            audio_history[class_name] = [ts for ts in audio_history[class_name] if now_ts - ts < 5.0]
                            
                            if len(audio_history[class_name]) >= 2:
                                event = EventData(
                                    camera_id=self.camera_id,
                                    camera_name=self.camera_name,
                                    event_type=class_name,
                                    severity=EventSeverity.HIGH,
                                    score=score,
                                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                                    source="audio_detection",
                                    payload={"confidence": score, "class_name": class_name}
                                )
                                self._fusion_service.ingest(event)
                                audio_history[class_name].clear()
                                
            except Exception as e:
                import re
                err_msg = str(e)
                # Redact passwords in rtsp URLs (e.g. rtsp://admin:pass@ip -> rtsp://admin:***@ip)
                err_msg = re.sub(r'(rtsp://[^:]+:)[^@]+(@)', r'\1***\2', err_msg)
                logger.warning("Audio loop exception for %s: %s", self.camera_name, err_msg)
                time.sleep(2)
            finally:
                if container:
                    try:
                        container.close()
                    except:
                        pass
