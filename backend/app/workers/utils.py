"""Utilities for the RTSP Detection Worker.

Includes frame preprocessing, image saving, and timing helpers.
"""
from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Tuple

import cv2

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


def ensure_dir(path: str) -> None:
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def save_frame_as_jpeg(frame, path: str, quality: int = 90) -> str:
    """Save BGR frame as JPEG and return path. Creates parent dir if needed."""
    ensure_dir(os.path.dirname(path))
    # OpenCV expects BGR image
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    success = cv2.imwrite(path, frame, encode_params)
    if not success:
        logger.error("Failed to write image to %s", path)
        raise IOError(f"Failed to write image to {path}")
    return path


def resize_frame_for_model(frame: "np.ndarray", target_size: Tuple[int, int]) -> "np.ndarray":
    """Resize frame preserving aspect ratio by letterbox if needed for YOLO models.
    Simple resize used as default; detectors may implement own preprocessing.
    """

    h, w = frame.shape[:2]
    tw, th = target_size
    if (w, h) == (tw, th):
        return frame
    resized = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_LINEAR)
    return resized


class Timer:
    """Simple timer for measuring durations."""

    def __init__(self) -> None:
        self._start: float | None = None

    def start(self) -> None:
        self._start = time.time()

    def elapsed_ms(self) -> float:
        if self._start is None:
            return 0.0
        return (time.time() - self._start) * 1000.0
