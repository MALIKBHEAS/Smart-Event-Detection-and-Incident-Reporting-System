"""FEATURE 3 -- Pattern Detection, FEATURE 4 -- Incident Clustering."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from app.intelligence.repositories.analytics_repository import AnalyticsRepository
from app.intelligence.schemas.analytics import IncidentCluster, Pattern
from app.intelligence.services.analytics_service import classify_category

REPEATED_SHARE_THRESHOLD = 0.4
REPEATED_HOUR_THRESHOLD = 0.25
REPEATED_TODAY_MIN_COUNT = 3


class PatternService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    # -- FEATURE 4: clustering ------------------------------------------

    def clusters(self, since: Optional[datetime] = None, limit: int = 50) -> List[IncidentCluster]:
        """Represent each Report as a cluster of the events fused into it,
        instead of surfacing every raw detection as its own line item."""
        reports = self.repository.recent_reports(since=since, limit=limit)
        clusters: List[IncidentCluster] = []
        for report in reports:
            report_id = int(report.id)
            incident_type: Optional[str] = str(report.incident_type) if report.incident_type is not None else None
            camera_id: Optional[int] = int(report.camera_id) if report.camera_id is not None else None
            occurrences = max(self.repository.event_count_for_report(report_id), 1)
            first_seen, last_seen = self.repository.event_time_span_for_report(report_id)
            duration = None
            if first_seen is not None and last_seen is not None:
                duration = max((last_seen - first_seen).total_seconds(), 0.0)
            clusters.append(
                IncidentCluster(
                    report_id=report_id,
                    incident_type=incident_type,
                    category=classify_category(incident_type),
                    severity=str(report.severity),
                    camera_id=camera_id,
                    camera_name=report.camera.name if report.camera else None,
                    occurrences=occurrences,
                    first_seen=first_seen.isoformat() if first_seen else (report.occurred_at.isoformat() if report.occurred_at else None),
                    last_seen=last_seen.isoformat() if last_seen else None,
                    duration_seconds=duration,
                )
            )
        return clusters

    # -- FEATURE 3: patterns ---------------------------------------------

    def patterns(self, since: Optional[datetime] = None) -> List[Pattern]:
        patterns: List[Pattern] = []
        total = self.repository.total_incidents(since=since)
        if total == 0:
            return patterns

        # repeated type
        type_counts = self.repository.incidents_by_field("incident_type", since=since)
        if type_counts:
            top_type, top_type_count = type_counts[0]
            share = top_type_count / total
            if share >= REPEATED_SHARE_THRESHOLD and top_type:
                patterns.append(
                    Pattern(
                        kind="repeated_type",
                        description=f"'{top_type}' accounts for {share * 100:.0f}% of incidents ({top_type_count} of {total}).",
                        strength=round(share, 2),
                    )
                )

        # repeated camera
        camera_counts = self.repository.incidents_by_camera(since=since)
        if camera_counts:
            top_cam_id, top_cam_name, top_cam_count = camera_counts[0]
            share = top_cam_count / total
            if share >= REPEATED_SHARE_THRESHOLD and top_cam_id is not None:
                patterns.append(
                    Pattern(
                        kind="repeated_camera",
                        description=f"{top_cam_name or f'Camera {top_cam_id}'} generated {share * 100:.0f}% of incidents ({top_cam_count} of {total}).",
                        strength=round(share, 2),
                    )
                )

        # repeated hour-of-day (from raw events, which carry finer-grained
        # timestamps than incidents)
        hour_counts = self.repository.events_by_hour(since=since)
        total_events = sum(c for _, c in hour_counts)
        if hour_counts and total_events > 0:
            top_hour, top_hour_count = max(hour_counts, key=lambda row: row[1])
            share = top_hour_count / total_events
            if share >= REPEATED_HOUR_THRESHOLD:
                patterns.append(
                    Pattern(
                        kind="repeated_hour",
                        description=f"Detections cluster around {top_hour}:00 ({share * 100:.0f}% of all events).",
                        strength=round(share, 2),
                    )
                )

        # repeated today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_type_counts = self.repository.incidents_by_field("incident_type", since=today_start)
        for itype, count in today_type_counts:
            if count >= REPEATED_TODAY_MIN_COUNT and itype:
                today_total = sum(c for _, c in today_type_counts)
                patterns.append(
                    Pattern(
                        kind="repeated_today",
                        description=f"'{itype}' happened {count} times today.",
                        strength=round(count / today_total, 2) if today_total else 0.0,
                    )
                )

        return patterns


def default_window(days: int = 30) -> datetime:
    return datetime.utcnow() - timedelta(days=days)
