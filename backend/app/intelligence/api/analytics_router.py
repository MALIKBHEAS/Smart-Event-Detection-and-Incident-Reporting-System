"""REST endpoints for the Intelligence & Analytics module (FEATURE 12)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.intelligence.repositories.analytics_repository import AnalyticsRepository
from app.intelligence.schemas.analytics import (
    AnomaliesResponse,
    CameraRisk,
    CamerasAnalyticsResponse,
    ExecutiveSummaryResponse,
    HotspotsResponse,
    IncidentCluster,
    IncidentsResponse,
    OverviewResponse,
    RecommendationsResponse,
    RiskResponse,
    TrendsResponse,
)
from app.intelligence.services.analytics_service import AnalyticsService
from app.intelligence.services.anomaly_service import AnomalyService
from app.intelligence.services.pattern_service import PatternService
from app.intelligence.services.recommendation_service import RecommendationService
from app.intelligence.services.risk_service import RiskService, risk_level_for_score

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)])


def _since_from_days(days: Optional[int]) -> Optional[datetime]:
    if days is None:
        return None
    return datetime.utcnow() - timedelta(days=days)


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    days: Optional[int] = Query(30, ge=1, le=3650, description="Lookback window in days"),
    db: Session = Depends(get_db),
) -> OverviewResponse:
    service = AnalyticsService(AnalyticsRepository(db))
    return service.overview(since=_since_from_days(days))


@router.get("/trends", response_model=TrendsResponse)
def get_trends(db: Session = Depends(get_db)) -> TrendsResponse:
    service = AnalyticsService(AnalyticsRepository(db))
    return service.trends()


@router.get("/risk", response_model=RiskResponse)
def get_risk(
    days: Optional[int] = Query(30, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> RiskResponse:
    repo = AnalyticsRepository(db)
    risk_service = RiskService(repo)
    since = _since_from_days(days)
    overall_score, overall_level = risk_service.score_overall(since=since)
    by_camera = [
        CameraRisk(camera_id=cid, camera_name=name, risk_score=score, risk_level=level, incident_count=count)
        for cid, name, score, level, count in risk_service.score_all_cameras(since=since)
    ]
    return RiskResponse(overall_risk_score=overall_score, overall_risk_level=overall_level, by_camera=by_camera)


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    days: Optional[int] = Query(30, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> RecommendationsResponse:
    service = RecommendationService(AnalyticsRepository(db))
    return RecommendationsResponse(recommendations=service.generate(since=_since_from_days(days)))


@router.get("/cameras", response_model=CamerasAnalyticsResponse)
def get_cameras_analytics(
    days: Optional[int] = Query(30, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> CamerasAnalyticsResponse:
    service = AnalyticsService(AnalyticsRepository(db))
    return CamerasAnalyticsResponse(cameras=service.camera_health(since=_since_from_days(days)))


@router.get("/incidents", response_model=IncidentsResponse)
def get_incidents_analytics(
    days: Optional[int] = Query(30, ge=1, le=3650),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> IncidentsResponse:
    repo = AnalyticsRepository(db)
    service = PatternService(repo)
    since = _since_from_days(days)
    clusters: list[IncidentCluster] = service.clusters(since=since, limit=limit)
    patterns = service.patterns(since=since)
    return IncidentsResponse(clusters=clusters, patterns=patterns)


@router.get("/summary", response_model=ExecutiveSummaryResponse)
def get_summary(
    hours: int = Query(24, ge=1, le=24 * 90, description="Lookback window in hours"),
    db: Session = Depends(get_db),
) -> ExecutiveSummaryResponse:
    from app.intelligence.services.summary_service import SummaryService

    service = SummaryService(AnalyticsRepository(db))
    return service.executive_summary(hours=hours)


@router.get("/hotspots", response_model=HotspotsResponse)
def get_hotspots(
    days: Optional[int] = Query(30, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> HotspotsResponse:
    service = AnalyticsService(AnalyticsRepository(db))
    return service.hotspots(since=_since_from_days(days))


@router.get("/anomalies", response_model=AnomaliesResponse)
def get_anomalies(db: Session = Depends(get_db)) -> AnomaliesResponse:
    service = AnomalyService(AnalyticsRepository(db))
    return AnomaliesResponse(anomalies=service.detect())


# Keep risk_level_for_score importable from this module for tests that only
# want the pure banding function without a DB session.
__all__ = ["router", "risk_level_for_score"]
