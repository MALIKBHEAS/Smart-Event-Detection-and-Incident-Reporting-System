"""Domain event model for the Event Fusion Engine."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any, Dict

EventPayload = Dict[str, Any]


class EventSeverity(str, Enum):
    """Severity levels used by the event fusion domain."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def from_score(cls, score: float) -> "EventSeverity":
        if score >= 0.8:
            return cls.HIGH
        if score >= 0.5:
            return cls.MEDIUM
        return cls.LOW

    @property
    def rank(self) -> int:
        return {self.LOW: 1, self.MEDIUM: 2, self.HIGH: 3}[self]


@dataclass
class EventData:
    """Domain representation of a fused security event."""

    camera_id: int
    camera_name: str
    event_type: str
    severity: EventSeverity
    score: float
    timestamp: datetime
    payload: EventPayload = field(default_factory=dict)
    source: str = "detection"
    screenshot_path: str | None = None
    id: int | None = None
    # Optional associated report id; None for events that are not yet tied to a report
    report_id: int | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "score": self.score,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "source": self.source,
            "screenshot_path": self.screenshot_path,
        }

    def with_severity(self, severity: EventSeverity) -> "EventData":
        return replace(self, severity=severity)
