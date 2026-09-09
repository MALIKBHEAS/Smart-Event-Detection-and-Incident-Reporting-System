from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CameraCount(BaseModel):
    camera_id: Optional[int]
    camera_name: Optional[str]
    count: int


class BucketCount(BaseModel):
    bucket: str
    count: int


class OverviewResponse(BaseModel):
    """FEATURE 1 -- event analytics."""

    total_detections: int
    total_incidents: int
    incidents_by_camera: List[CameraCount]
    incidents_by_day: List[BucketCount]
    incidents_by_week: List[BucketCount]
    incidents_by_month: List[BucketCount]
    incidents_by_category: List[BucketCount]
    incidents_by_severity: List[BucketCount]


class TrendPoint(BaseModel):
    label: str
    current: int
    previous: int
    direction: str  # "up" | "down" | "stable"
    change_pct: Optional[float]


class TrendsResponse(BaseModel):
    """FEATURE 8 -- trend analysis."""

    trends: List[TrendPoint]


class CameraRisk(BaseModel):
    camera_id: int
    camera_name: str
    risk_score: float
    risk_level: str
    incident_count: int


class RiskResponse(BaseModel):
    """FEATURE 5 -- risk score."""

    overall_risk_score: float
    overall_risk_level: str
    by_camera: List[CameraRisk]


class Recommendation(BaseModel):
    title: str
    detail: str
    priority: str  # "low" | "medium" | "high"
    related_camera_id: Optional[int] = None


class RecommendationsResponse(BaseModel):
    """FEATURE 9 -- smart recommendations."""

    recommendations: List[Recommendation]


class CameraHealth(BaseModel):
    """FEATURE 11 -- camera health analytics."""

    camera_id: int
    camera_name: str
    enabled: bool
    incidents_generated: int
    average_confidence: Optional[float]
    last_incident_at: Optional[str]
    risk_score: float
    risk_level: str
    # Not tracked anywhere in the current pipeline (no frame/FPS telemetry is
    # persisted), so these are explicitly surfaced as unavailable rather than
    # guessed -- see the Future AI Enhancements note in the final report.
    availability_pct: Optional[float] = None
    average_fps: Optional[float] = None
    dropped_frames: Optional[int] = None


class CamerasAnalyticsResponse(BaseModel):
    cameras: List[CameraHealth]


class IncidentCluster(BaseModel):
    """FEATURE 4 -- incident clustering."""

    report_id: Optional[int]
    incident_type: Optional[str]
    category: str
    severity: str
    camera_id: Optional[int]
    camera_name: Optional[str]
    occurrences: int
    first_seen: Optional[str]
    last_seen: Optional[str]
    duration_seconds: Optional[float]


class Pattern(BaseModel):
    """FEATURE 3 -- pattern detection."""

    kind: str  # "repeated_type" | "repeated_camera" | "repeated_hour" | "repeated_today"
    description: str
    strength: float  # 0-1, share of total incidents this pattern accounts for


class IncidentsResponse(BaseModel):
    clusters: List[IncidentCluster]
    patterns: List[Pattern]


class ExecutiveSummaryResponse(BaseModel):
    """FEATURE 10 -- AI summary."""

    window_label: str
    total_events: int
    total_incidents: int
    highest_risk_camera: Optional[str]
    most_frequent_event: Optional[str]
    peak_activity_window: Optional[str]
    overall_risk_level: str
    recommended_action: Optional[str]
    narrative: str


class Hotspot(BaseModel):
    kind: str  # "camera" | "hour" | "day"
    label: str
    count: int
    share_pct: float


class HotspotsResponse(BaseModel):
    """FEATURE 6 -- hotspot analysis."""

    highest_risk_camera: Optional[Hotspot]
    busiest_hour: Optional[Hotspot]
    most_dangerous_day: Optional[Hotspot]
    hotspots: List[Hotspot]


class Anomaly(BaseModel):
    kind: str
    description: str
    anomaly_score: float  # 0-1
    context: Dict[str, Any]


class AnomaliesResponse(BaseModel):
    """FEATURE 7 -- anomaly detection."""

    anomalies: List[Anomaly]
