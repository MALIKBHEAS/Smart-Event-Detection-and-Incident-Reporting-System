"""FEATURE 1 -- Event Analytics, FEATURE 2 -- Event Classification,
FEATURE 11 -- Camera Health Analytics."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Optional

from app.intelligence.repositories.analytics_repository import AnalyticsRepository
from app.intelligence.schemas.analytics import (
    BucketCount,
    CameraCount,
    CameraHealth,
    Hotspot,
    HotspotsResponse,
    OverviewResponse,
    TrendPoint,
    TrendsResponse,
)
from app.intelligence.services.risk_service import RiskService

# FEATURE 2: rule-based classification. Matches the detector names actually
# emitted by app.workers.detectors (restricted_area, line_crossing,
# loitering, suspicious_object) plus common keywords for categories the
# current detector set doesn't produce yet (fire, network, safety), so the
# taxonomy is ready for those detectors without further changes here.
_CATEGORY_KEYWORDS = [
    ("Fire", ("fire", "smoke", "flame")),
    ("Network", ("network", "offline", "disconnect", "camera_down", "connection")),
    ("Safety", ("safety", "ppe", "helmet", "hazard")),
    ("Unauthorized Access", ("restricted_area", "unauthorized", "access", "door", "intrusion")),
    ("Suspicious Object", ("suspicious_object", "abandoned", "unattended")),
    ("Security", ("line_crossing", "loitering", "perimeter", "trespass")),
]


def classify_category(incident_type: Optional[str]) -> str:
    if not incident_type:
        return "Other"
    lowered = incident_type.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        for keyword in keywords:
            # \w-boundary match: avoids false positives like "ppe" matching
            # inside "unmapped" from plain substring containment.
            if re.search(rf"(?:^|[^a-z0-9]){re.escape(keyword)}(?:[^a-z0-9]|$)", lowered):
                return category
    return "Other"


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository
        self.risk_service = RiskService(repository)

    # -- FEATURE 1 --------------------------------------------------------

    def overview(self, since: Optional[datetime] = None) -> OverviewResponse:
        by_type = self.repository.incidents_by_field("incident_type", since=since)
        category_totals: dict[str, int] = {}
        for itype, count in by_type:
            category = classify_category(itype)
            category_totals[category] = category_totals.get(category, 0) + count

        severity_counts = self.repository.incidents_by_field("severity", since=since)

        return OverviewResponse(
            total_detections=self.repository.total_events(since=since),
            total_incidents=self.repository.total_incidents(since=since),
            incidents_by_camera=[
                CameraCount(camera_id=cid, camera_name=name, count=count)
                for cid, name, count in self.repository.incidents_by_camera(since=since)
            ],
            incidents_by_day=[
                BucketCount(bucket=b, count=c) for b, c in self.repository.incidents_by_bucket("day", since=since)
            ],
            incidents_by_week=[
                BucketCount(bucket=b, count=c) for b, c in self.repository.incidents_by_bucket("week", since=since)
            ],
            incidents_by_month=[
                BucketCount(bucket=b, count=c) for b, c in self.repository.incidents_by_bucket("month", since=since)
            ],
            incidents_by_category=[
                BucketCount(bucket=cat, count=count) for cat, count in sorted(category_totals.items(), key=lambda kv: -kv[1])
            ],
            incidents_by_severity=[
                BucketCount(bucket=(sev or "unknown"), count=count) for sev, count in severity_counts
            ],
        )

    # -- FEATURE 11 ---------------------------------------------------------

    def camera_health(self, since: Optional[datetime] = None) -> List[CameraHealth]:
        results: List[CameraHealth] = []
        incident_counts: dict[int, int] = {
            int(cid): count for cid, _name, count in self.repository.incidents_by_camera(since=since) if cid is not None
        }

        for camera in self.repository.cameras():
            camera_id = int(camera.id)
            camera_name = str(camera.name)
            score, level, _count_in_window = self.risk_service.score_camera(camera_id, since=since)
            payloads = self.repository.recent_event_payloads_for_camera(camera_id, since=since)
            confidences = [
                float(p["score"])
                for p in payloads
                if isinstance(p, dict) and isinstance(p.get("score"), (int, float))
            ]
            avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else None
            last_incident = self.repository.last_incident_at_for_camera(camera_id)

            results.append(
                CameraHealth(
                    camera_id=camera_id,
                    camera_name=camera_name,
                    enabled=bool(camera.enabled),
                    incidents_generated=incident_counts.get(camera_id, 0),
                    average_confidence=avg_confidence,
                    last_incident_at=last_incident.isoformat() if last_incident else None,
                    risk_score=score,
                    risk_level=level,
                )
            )
        results.sort(key=lambda c: c.incidents_generated, reverse=True)
        return results

    # -- FEATURE 6 ----------------------------------------------------------

    def hotspots(self, since: Optional[datetime] = None) -> HotspotsResponse:
        total = self.repository.total_incidents(since=since)
        camera_counts = self.repository.incidents_by_camera(since=since)
        by_field = self.repository.incidents_by_field

        def to_hotspot(kind: str, label: Optional[str], count: int, denom: int) -> Optional[Hotspot]:
            if not label or denom == 0:
                return None
            return Hotspot(kind=kind, label=str(label), count=count, share_pct=round((count / denom) * 100, 1))

        highest_risk_camera = None
        if camera_counts:
            cid, name, count = camera_counts[0]
            highest_risk_camera = to_hotspot("camera", name or (f"Camera {cid}" if cid else None), count, total)

        hour_counts = self.repository.events_by_hour(since=since)
        total_events = sum(c for _, c in hour_counts)
        busiest_hour = None
        if hour_counts and total_events:
            hour, count = max(hour_counts, key=lambda row: row[1])
            busiest_hour = to_hotspot("hour", f"{hour}:00", count, total_events)

        # "day" here means day-of-week, distinct from the day-bucket used in
        # the overview trend (which is calendar date).
        day_of_week_counts: dict[str, int] = {}
        for report in self.repository.recent_reports(since=since, limit=2000):
            if report.created_at is None:
                continue
            day_of_week_counts[report.created_at.strftime("%A")] = day_of_week_counts.get(
                report.created_at.strftime("%A"), 0
            ) + 1
        most_dangerous_day = None
        if day_of_week_counts:
            day, count = max(day_of_week_counts.items(), key=lambda kv: kv[1])
            most_dangerous_day = to_hotspot("day", day, count, sum(day_of_week_counts.values()))

        hotspots = [h for h in (highest_risk_camera, busiest_hour, most_dangerous_day) if h is not None]
        return HotspotsResponse(
            highest_risk_camera=highest_risk_camera,
            busiest_hour=busiest_hour,
            most_dangerous_day=most_dangerous_day,
            hotspots=hotspots,
        )

    # -- FEATURE 8 ----------------------------------------------------------

    def trends(self, now: Optional[datetime] = None) -> TrendsResponse:
        now = now or datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=today_start.weekday())
        last_week_start = week_start - timedelta(days=7)
        month_start = today_start.replace(day=1)
        last_month_end = month_start - timedelta(seconds=1)
        last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def count_between(start: datetime, end: Optional[datetime]) -> int:
            query_since = start
            total_from_since = self.repository.total_incidents(since=query_since)
            if end is None:
                return total_from_since
            total_from_end = self.repository.total_incidents(since=end)
            return total_from_since - total_from_end

        points = [
            ("Today vs Yesterday", count_between(today_start, None), count_between(yesterday_start, today_start)),
            ("This Week vs Last Week", count_between(week_start, None), count_between(last_week_start, week_start)),
            ("This Month vs Last Month", count_between(month_start, None), count_between(last_month_start, month_start)),
        ]

        trend_points = []
        for label, current, previous in points:
            if previous == 0:
                direction = "up" if current > 0 else "stable"
                change_pct = None
            else:
                change = (current - previous) / previous
                change_pct = round(change * 100, 1)
                direction = "up" if change > 0.05 else "down" if change < -0.05 else "stable"
            trend_points.append(TrendPoint(label=label, current=current, previous=previous, direction=direction, change_pct=change_pct))

        return TrendsResponse(trends=trend_points)
