"""Registry and factory for computer-vision (object) detectors.

This module provides pluggable CV detector registration. Full YOLO integration
is deferred to a later phase; the registry wires existing plugins lazily and
provides a lightweight noop detector for tests.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List

from app.domain.detection import BaseDetector, RawDetection

logger = logging.getLogger(__name__)

DetectorFactory = Callable[..., BaseDetector]

_REGISTRY: Dict[str, DetectorFactory] = {}


class NoOpDetector:
    """Lightweight detector that returns no detections."""

    def detect(self, frame: Any, conf: float = 0.5) -> List[RawDetection]:
        return []


def register_detector(name: str, factory: DetectorFactory) -> None:
    """Register a detector factory under a canonical lowercase name."""
    _REGISTRY[name.lower()] = factory


def _noop_factory(**kwargs: Any) -> BaseDetector:
    return NoOpDetector()


def _yolo_factory(**kwargs: Any) -> BaseDetector:
    from app.plugins.cv.yolo_detector import YOLODetector

    return YOLODetector(**kwargs)


def _ensure_builtin_detectors() -> None:
    if "noop" not in _REGISTRY:
        register_detector("noop", _noop_factory)
    if "yolo" not in _REGISTRY:
        register_detector("yolo", _yolo_factory)


def get_detector(name: str, **kwargs: Any) -> BaseDetector:
    """Instantiate a registered detector by name."""
    _ensure_builtin_detectors()
    factory = _REGISTRY.get(name.lower())
    if factory is None:
        raise ValueError(f"Unknown CV detector '{name}'")
    return factory(**kwargs)


def default_detector(**kwargs: Any) -> BaseDetector:
    """Return the default CV detector.

    Prefers the existing YOLO plugin when available; otherwise falls back to
    the noop detector so workers can start without heavy model dependencies.
    """
    _ensure_builtin_detectors()
    try:
        from app.plugins.cv.yolo_detector import YOLODetector

        if YOLODetector is not None:
            return YOLODetector(**kwargs)
    except Exception:
        logger.debug("YOLO detector unavailable; using noop detector")
    return NoOpDetector()


def list_registered_detectors() -> List[str]:
    """Return sorted names of registered detectors."""
    _ensure_builtin_detectors()
    return sorted(_REGISTRY.keys())
