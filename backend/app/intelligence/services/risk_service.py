"""FEATURE 5 -- Risk Score.

Computes a 0-100 risk score from incident frequency, severity mix,
repetition (how concentrated incidents are in a few types), and camera
history. Independent of the pipeline's EventSeverity enum (low/medium/high)
since this module needs an extra "Critical" band on top for high-risk
aggregates -- adding a fourth value to the shared domain enum would ripple
into the core detection pipeline, which is out of scope here.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from app.intelligence.repositories.analytics_repository import AnalyticsRepository

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

# Incident counts at/above these are treated as "maxed out" for the
# frequency component of the score (i.e. no extra risk credit past this).
CAMERA_WINDOW_SATURATION = 15
CAMERA_HISTORY_SATURATION = 60
OVERALL_SATURATION = 100


def risk_level_for_score(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Medium"
    return "Low"


def _severity_component(severity_counts: List[Tuple[Optional[str], int]]) -> float:
    total = sum(count for _, count in severity_counts)
    if total == 0:
        return 0.0
    weighted = sum(SEVERITY_RANK.get((sev or "low").lower(), 1) * count for sev, count in severity_counts)
    avg_rank = weighted / total
    # avg_rank ranges ~1..4 -> normalize to 0..1
    return min(max((avg_rank - 1) / 3, 0.0), 1.0)


def _repetition_component(type_counts: List[Tuple[Optional[str], int]]) -> float:
    total = sum(count for _, count in type_counts)
    if total == 0 or not type_counts:
        return 0.0
    top = max(count for _, count in type_counts)
    # share of incidents attributable to the single most common type
    return min(top / total, 1.0)


class RiskService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    def score_camera(self, camera_id: int, since: Optional[datetime] = None) -> Tuple[float, str, int]:
        """Returns (score, level, incident_count_in_window) for one camera."""
        type_counts = [
            (itype, count)
            for itype, cam_id, _cam_name, count in self.repository.incidents_by_type_and_camera(since=since)
            if cam_id == camera_id
        ]
        incident_count = sum(count for _, count in type_counts)

        severity_counts = self.repository.incidents_by_field("severity", since=since)
        # incidents_by_field isn't camera-scoped; approximate the camera's
        # severity mix by using the overall mix. This avoids an extra
        # per-camera query while still reflecting how severe incidents tend
        # to be system-wide.
        severity_component = _severity_component(severity_counts)

        freq_component = min(incident_count / CAMERA_WINDOW_SATURATION, 1.0)
        repetition_component = _repetition_component(type_counts)

        history_total = sum(
            count
            for _cam_id, _name, count in self.repository.incidents_by_camera()
            if _cam_id == camera_id
        )
        history_component = min(history_total / CAMERA_HISTORY_SATURATION, 1.0)

        score = (
            freq_component * 40
            + severity_component * 30
            + repetition_component * 15
            + history_component * 15
        )
        return round(score, 1), risk_level_for_score(score), incident_count

    def score_overall(self, since: Optional[datetime] = None) -> Tuple[float, str]:
        total = self.repository.total_incidents(since=since)
        severity_counts = self.repository.incidents_by_field("severity", since=since)
        type_counts = self.repository.incidents_by_field("incident_type", since=since)

        freq_component = min(total / OVERALL_SATURATION, 1.0)
        severity_component = _severity_component(severity_counts)
        repetition_component = _repetition_component(type_counts)

        score = freq_component * 45 + severity_component * 35 + repetition_component * 20
        return round(score, 1), risk_level_for_score(score)

    def score_all_cameras(self, since: Optional[datetime] = None) -> List[Tuple[int, str, float, str, int]]:
        """Returns (camera_id, camera_name, score, level, incident_count) for
        every camera, sorted by descending risk."""
        results = []
        for camera in self.repository.cameras():
            camera_id = int(camera.id)
            camera_name = str(camera.name)
            score, level, count = self.score_camera(camera_id, since=since)
            results.append((camera_id, camera_name, score, level, count))
        results.sort(key=lambda row: row[2], reverse=True)
        return results


def default_window(days: int = 30) -> datetime:
    return datetime.utcnow() - timedelta(days=days)
