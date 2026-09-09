"""FEATURE 10 -- AI Summary.

Generates an executive summary from this module's own analytics --
deterministic template filling, not a live LLM call (see "Future AI
Enhancements" in the module's delivery notes for where a real LLM call
could slot in later, e.g. narrating `narrative` from these same fields).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.intelligence.repositories.analytics_repository import AnalyticsRepository
from app.intelligence.schemas.analytics import ExecutiveSummaryResponse
from app.intelligence.services.analytics_service import AnalyticsService
from app.intelligence.services.recommendation_service import RecommendationService
from app.intelligence.services.risk_service import RiskService


class SummaryService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository
        self.analytics_service = AnalyticsService(repository)
        self.risk_service = RiskService(repository)
        self.recommendation_service = RecommendationService(repository)

    def executive_summary(self, hours: int = 24) -> ExecutiveSummaryResponse:
        since = datetime.utcnow() - timedelta(hours=hours)
        window_label = f"the last {hours} hours"

        total_events = self.repository.total_events(since=since)
        total_incidents = self.repository.total_incidents(since=since)

        camera_scores = self.risk_service.score_all_cameras(since=since)
        highest_risk_camera = camera_scores[0][1] if camera_scores and camera_scores[0][4] > 0 else None

        type_counts = self.repository.incidents_by_field("incident_type", since=since)
        most_frequent_event = type_counts[0][0] if type_counts else None

        hour_counts = self.repository.events_by_hour(since=since)
        peak_activity_window = None
        if hour_counts:
            hour, _count = max(hour_counts, key=lambda row: row[1])
            hour_int = int(hour)
            peak_activity_window = f"{hour_int:02d}:00 - {(hour_int + 2) % 24:02d}:00"

        overall_score, overall_level = self.risk_service.score_overall(since=since)

        recommendations = self.recommendation_service.generate(since=since)
        recommended_action = recommendations[0].detail if recommendations else None

        narrative_lines = [
            f"During {window_label}:",
            f"{total_events} events detected.",
            f"{total_incidents} incidents generated.",
        ]
        if highest_risk_camera:
            narrative_lines.append(f"Highest risk camera: {highest_risk_camera}.")
        if most_frequent_event:
            narrative_lines.append(f"Most frequent event: {most_frequent_event}.")
        if peak_activity_window:
            narrative_lines.append(f"Peak activity: {peak_activity_window}.")
        narrative_lines.append(f"Overall risk: {overall_level.upper()}.")
        if recommended_action:
            narrative_lines.append(f"Recommended action: {recommended_action}")

        return ExecutiveSummaryResponse(
            window_label=window_label,
            total_events=total_events,
            total_incidents=total_incidents,
            highest_risk_camera=highest_risk_camera,
            most_frequent_event=most_frequent_event,
            peak_activity_window=peak_activity_window,
            overall_risk_level=overall_level,
            recommended_action=recommended_action,
            narrative=" ".join(narrative_lines),
        )
