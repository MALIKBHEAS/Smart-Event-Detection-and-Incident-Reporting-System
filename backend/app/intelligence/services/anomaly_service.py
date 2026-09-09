"""FEATURE 7 -- Anomaly Detection.

Flags unusual activity by comparing a short recent window against a longer
historical baseline (simple z-score-like ratio, not ML -- appropriate for
the aggregation-query-only performance constraint). Anomaly score is 0-1:
higher means further from the historical baseline.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from app.intelligence.repositories.analytics_repository import AnalyticsRepository
from app.intelligence.schemas.analytics import Anomaly

RECENT_WINDOW_HOURS = 24
BASELINE_WINDOW_DAYS = 14
SPIKE_RATIO_THRESHOLD = 2.0  # recent rate >= 2x the baseline daily rate


def _score_from_ratio(ratio: float) -> float:
    # Maps a rate ratio (recent / baseline) to a 0-1 anomaly score.
    # ratio <= threshold -> 0; ratio grows -> approaches 1.
    if ratio <= SPIKE_RATIO_THRESHOLD:
        return 0.0
    return round(min((ratio - SPIKE_RATIO_THRESHOLD) / SPIKE_RATIO_THRESHOLD, 1.0), 2)


class AnomalyService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    def detect(self, now: Optional[datetime] = None) -> List[Anomaly]:
        now = now or datetime.utcnow()
        recent_start = now - timedelta(hours=RECENT_WINDOW_HOURS)
        baseline_start = now - timedelta(days=BASELINE_WINDOW_DAYS)

        anomalies: List[Anomaly] = []

        # -- overall incident-rate spike -----------------------------------
        recent_total = self.repository.total_incidents(since=recent_start)
        baseline_total = self.repository.total_incidents(since=baseline_start)
        baseline_days = max(BASELINE_WINDOW_DAYS, 1)
        baseline_daily_rate = baseline_total / baseline_days
        if baseline_daily_rate > 0:
            ratio = recent_total / baseline_daily_rate
        else:
            ratio = float(recent_total) if recent_total > 0 else 0.0
        score = _score_from_ratio(ratio)
        if score > 0:
            anomalies.append(
                Anomaly(
                    kind="incident_rate_spike",
                    description=(
                        f"Incidents in the last {RECENT_WINDOW_HOURS}h ({recent_total}) are "
                        f"{ratio:.1f}x the {BASELINE_WINDOW_DAYS}-day average daily rate "
                        f"({baseline_daily_rate:.1f}/day)."
                    ),
                    anomaly_score=score,
                    context={"recent_total": recent_total, "baseline_daily_rate": round(baseline_daily_rate, 2)},
                )
            )

        # -- per-camera unexpected behavior ----------------------------------
        recent_by_camera = {cid: count for cid, _n, count in self.repository.incidents_by_camera(since=recent_start)}
        baseline_by_camera = {
            cid: count for cid, _n, count in self.repository.incidents_by_camera(since=baseline_start)
        }
        camera_names: dict[int, str] = {int(c.id): str(c.name) for c in self.repository.cameras()}
        for camera_id, recent_count in recent_by_camera.items():
            if camera_id is None:
                continue
            baseline_count = baseline_by_camera.get(camera_id, 0)
            baseline_daily = baseline_count / baseline_days
            if baseline_daily > 0:
                cam_ratio = recent_count / baseline_daily
            else:
                cam_ratio = float(recent_count) if recent_count > 0 else 0.0
            cam_score = _score_from_ratio(cam_ratio)
            if cam_score > 0:
                name = camera_names.get(camera_id, f"Camera {camera_id}")
                anomalies.append(
                    Anomaly(
                        kind="camera_activity_spike",
                        description=(
                            f"{name} logged {recent_count} incidents in the last "
                            f"{RECENT_WINDOW_HOURS}h vs a baseline of {baseline_daily:.1f}/day."
                        ),
                        anomaly_score=cam_score,
                        context={"camera_id": camera_id, "recent_count": recent_count, "baseline_daily": round(baseline_daily, 2)},
                    )
                )

        # -- unexpected incident-type frequency -------------------------------
        recent_types = dict(self.repository.incidents_by_field("incident_type", since=recent_start))
        baseline_types = dict(self.repository.incidents_by_field("incident_type", since=baseline_start))
        for itype, recent_count in recent_types.items():
            if not itype:
                continue
            baseline_count = baseline_types.get(itype, 0)
            baseline_daily = baseline_count / baseline_days
            if baseline_daily > 0:
                type_ratio = recent_count / baseline_daily
            else:
                type_ratio = float(recent_count) if recent_count > 0 else 0.0
            type_score = _score_from_ratio(type_ratio)
            if type_score > 0:
                anomalies.append(
                    Anomaly(
                        kind="event_type_spike",
                        description=(
                            f"'{itype}' occurred {recent_count} times in the last "
                            f"{RECENT_WINDOW_HOURS}h vs a baseline of {baseline_daily:.1f}/day."
                        ),
                        anomaly_score=type_score,
                        context={"incident_type": itype, "recent_count": recent_count, "baseline_daily": round(baseline_daily, 2)},
                    )
                )

        anomalies.sort(key=lambda a: a.anomaly_score, reverse=True)
        return anomalies
