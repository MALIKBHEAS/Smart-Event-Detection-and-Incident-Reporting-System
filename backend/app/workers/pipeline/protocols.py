from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.workers.pipeline.context import FrameContext, ProcessedFrame


@runtime_checkable
class FrameProcessorProtocol(Protocol):
    """Protocol for frame-level detection pipeline processors."""

    def process(self, context: FrameContext) -> ProcessedFrame:
        """Run detection, tracking, and event detection for one frame."""
        ...
