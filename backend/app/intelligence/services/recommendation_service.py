"""FEATURE 9 -- Smart Recommendations.

Rule-based recommendations derived entirely from this module's own
analytics output (risk scores, patterns, anomalies) -- not a separate
opinion layer, so every recommendation traces back to a concrete number.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.intelligence.repositories.analytics_repository import AnalyticsRepository
from app.intelligence.schemas.analytics import Recommendation
from app.intelligence.services.analytics_service import classify_category
from app.intelligence.services.anomaly_service import AnomalyService
from app.intelligence.services.pattern_service import PatternService
from app.intelligence.services.risk_service import RiskService

NIGHT_HOURS = {"00", "01", "02", "03", "04", "05"}


class RecommendationService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository
        self.risk_service = RiskService(repository)
        self.pattern_service = PatternService(repository)
        self.anomaly_service = AnomalyService(repository)

    def generate(self, since: Optional[datetime] = None) -> List[Recommendation]:
        recs: List[Recommendation] = []

        # High/critical-risk cameras
        for camera_id, camera_name, score, level, count in self.risk_service.score_all_cameras(since=since):
            if level in ("High", "Critical") and count > 0:
                priority = "high" if level == "Critical" else "medium"
                recs.append(
                    Recommendation(
                        title=f"Review {camera_name}",
                        detail=(
                            f"{camera_name} has a {level.lower()} risk score ({score}/100) from "
                            f"{count} recent incident(s). Review footage and consider increasing "
                            f"patrol frequency in this area."
                        ),
                        priority=priority,
                        related_camera_id=camera_id,
                    )
                )

        # Repeated-camera / repeated-type patterns
        for pattern in self.pattern_service.patterns(since=since):
            if pattern.kind == "repeated_camera" and pattern.strength >= 0.5:
                recs.append(
                    Recommendation(
                        title="Consider an additional camera",
                        detail=(
                            f"{pattern.description} A second vantage point may reduce blind spots "
                            f"driving this concentration."
                        ),
                        priority="medium",
                    )
                )
            if pattern.kind == "repeated_hour":
                hour_label = pattern.description.split("around ")[-1].split(" ")[0].rstrip(":00")
                if hour_label in NIGHT_HOURS or pattern.description.split("around ")[-1][:2] in NIGHT_HOURS:
                    recs.append(
                        Recommendation(
                            title="Improve lighting",
                            detail=f"{pattern.description} Overnight activity often correlates with poor lighting -- consider a lighting audit.",
                            priority="medium",
                        )
                    )

        # Category-driven recommendations
        by_type = self.repository.incidents_by_field("incident_type", since=since)
        categories_present = {classify_category(itype) for itype, _count in by_type}
        if "Network" in categories_present:
            recs.append(
                Recommendation(
                    title="Review network security",
                    detail="Network-related incidents were detected. Audit camera connectivity, VPN access, and firewall rules.",
                    priority="medium",
                )
            )
        if "Fire" in categories_present:
            recs.append(
                Recommendation(
                    title="Inspect fire safety equipment",
                    detail="Fire/smoke-related incidents were detected. Verify extinguishers, alarms, and evacuation routes near affected cameras.",
                    priority="high",
                )
            )
        if "Unauthorized Access" in categories_present:
            recs.append(
                Recommendation(
                    title="Increase patrol frequency",
                    detail="Unauthorized access incidents were detected. Increase patrol frequency and consider access-control hardware at affected entry points.",
                    priority="high",
                )
            )

        # Anomalies
        for anomaly in self.anomaly_service.detect():
            if anomaly.anomaly_score >= 0.5:
                recs.append(
                    Recommendation(
                        title="Investigate unusual activity",
                        detail=anomaly.description,
                        priority="high" if anomaly.anomaly_score >= 0.75 else "medium",
                        related_camera_id=anomaly.context.get("camera_id"),
                    )
                )

        # De-duplicate by (title, related_camera_id), keep highest priority
        priority_rank = {"high": 3, "medium": 2, "low": 1}
        deduped: dict = {}
        for rec in recs:
            key = (rec.title, rec.related_camera_id)
            existing = deduped.get(key)
            if existing is None or priority_rank[rec.priority] > priority_rank[existing.priority]:
                deduped[key] = rec

        result = list(deduped.values())
        result.sort(key=lambda r: priority_rank[r.priority], reverse=True)
        return result
