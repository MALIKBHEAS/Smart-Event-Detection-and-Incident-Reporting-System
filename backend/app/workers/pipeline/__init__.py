"""Detection pipeline package for frame-level processing."""

from app.workers.pipeline.context import FrameContext, ProcessedFrame
from app.workers.pipeline.cv_detector_registry import (
    default_detector,
    get_detector,
    register_detector,
)
from app.workers.pipeline.frame_processor import DetectionFrameProcessor
from app.workers.pipeline.protocols import FrameProcessorProtocol

__all__ = [
    "FrameContext",
    "ProcessedFrame",
    "DetectionFrameProcessor",
    "FrameProcessorProtocol",
    "default_detector",
    "get_detector",
    "register_detector",
]
