from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from app.auth.dependencies import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.intelligence.repositories.analytics_repository import AnalyticsRepository
from app.intelligence.services.analytics_service import AnalyticsService, classify_category
from app.intelligence.services.anomaly_service import AnomalyService
from app.intelligence.services.pattern_service import PatternService
from app.intelligence.services.recommendation_service import RecommendationService
from app.intelligence.services.risk_service import RiskService, risk_level_for_score
from app.intelligence.services.summary_service import SummaryService
from app.main import app
from app.models.camera import Camera
from app.models.event import Event
from app.models.report import Report
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Pure unit tests -- no DB involved
# ---------------------------------------------------------------------------


def test_classify_category_matches_known_detector_names() -> None:
    assert classify_category("restricted_area") == "Unauthorized Access"
    assert classify_category("line_crossing") == "Security"
    assert classify_category("loitering") == "Security"
    assert classify_category("suspicious_object") == "Suspicious Object"
    assert classify_category("fire_alarm") == "Fire"
    assert classify_category("camera_down") == "Network"
    assert classify_category(None) == "Other"
    assert classify_category("something_unmapped") == "Other"


def test_risk_level_banding() -> None:
    assert risk_level_for_score(0) == "Low"
    assert risk_level_for_score(24.9) == "Low"
    assert risk_level_for_score(25) == "Medium"
    assert risk_level_for_score(49.9) == "Medium"
    assert risk_level_for_score(50) == "High"
    assert risk_level_for_score(74.9) == "High"
    assert risk_level_for_score(75) == "Critical"
    assert risk_level_for_score(100) == "Critical"


# ---------------------------------------------------------------------------
# Integration tests against a seeded in-memory database
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    session: Session = SessionFactory()

    now = datetime.utcnow()

    hot_camera = Camera(name="Hot Camera", rtsp_url="rtsp://hot", location="Dock", enabled=True)
    quiet_camera = Camera(name="Quiet Camera", rtsp_url="rtsp://quiet", location="Lobby", enabled=True)
    session.add_all([hot_camera, quiet_camera])
    session.commit()
    session.refresh(hot_camera)
    session.refresh(quiet_camera)

    # 6 recent, clustered "restricted_area" incidents on hot_camera (last 24h)
    for i in range(6):
        report = Report(
            title=f"Restricted area breach {i}",
            summary="test incident",
            incident_type="restricted_area",
            severity="high",
            status="open",
            camera_id=hot_camera.id,
            occurred_at=now - timedelta(hours=i),
            created_at=now - timedelta(hours=i),
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        for j in range(3):
            session.add(
                Event(
                    camera_id=hot_camera.id,
                    report_id=report.id,
                    type="restricted_area",
                    severity="high",
                    timestamp=now - timedelta(hours=i, minutes=j * 2),
                    payload={"score": 0.9},
                )
            )
        session.commit()

    # 1 old, low-severity incident on quiet_camera (30 days ago -- outside
    # default 30-day-ish windows used by most tests here, but present so
    # "all cameras" listings aren't trivially single-row)
    old_report = Report(
        title="Old loitering event",
        summary="test",
        incident_type="loitering",
        severity="low",
        status="resolved",
        camera_id=quiet_camera.id,
        occurred_at=now - timedelta(days=45),
        created_at=now - timedelta(days=45),
    )
    session.add(old_report)
    session.commit()

    yield session, hot_camera, quiet_camera

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_repository_counts(db_session) -> None:
    session, hot_camera, _quiet = db_session
    repo = AnalyticsRepository(session)

    assert repo.total_incidents() == 7
    assert repo.total_events() == 18

    by_camera = {cid: count for cid, _name, count in repo.incidents_by_camera()}
    assert by_camera[hot_camera.id] == 6


def test_analytics_service_overview(db_session) -> None:
    session, hot_camera, _quiet = db_session
    service = AnalyticsService(AnalyticsRepository(session))

    overview = service.overview(since=datetime.utcnow() - timedelta(days=2))
    assert overview.total_incidents == 6
    assert overview.total_detections == 18
    assert overview.incidents_by_camera[0].camera_id == hot_camera.id
    categories = {b.bucket: b.count for b in overview.incidents_by_category}
    assert categories["Unauthorized Access"] == 6


def test_risk_service_flags_hot_camera_higher(db_session) -> None:
    session, hot_camera, quiet_camera = db_session
    risk_service = RiskService(AnalyticsRepository(session))

    hot_score, hot_level, hot_count = risk_service.score_camera(hot_camera.id, since=datetime.utcnow() - timedelta(days=2))
    quiet_score, _quiet_level, quiet_count = risk_service.score_camera(
        quiet_camera.id, since=datetime.utcnow() - timedelta(days=2)
    )

    assert hot_count == 6
    assert quiet_count == 0
    assert hot_score > quiet_score
    assert hot_level in ("High", "Critical")


def test_pattern_service_detects_repeated_camera_and_type(db_session) -> None:
    session, hot_camera, _quiet = db_session
    pattern_service = PatternService(AnalyticsRepository(session))

    patterns = pattern_service.patterns(since=datetime.utcnow() - timedelta(days=2))
    kinds = {p.kind for p in patterns}
    assert "repeated_camera" in kinds
    assert "repeated_type" in kinds


def test_pattern_service_clusters_aggregate_event_occurrences(db_session) -> None:
    session, hot_camera, _quiet = db_session
    pattern_service = PatternService(AnalyticsRepository(session))

    clusters = pattern_service.clusters(since=datetime.utcnow() - timedelta(days=2))
    assert len(clusters) == 6
    for cluster in clusters:
        assert cluster.occurrences == 3
        assert cluster.camera_id == hot_camera.id
        assert cluster.category == "Unauthorized Access"
        assert cluster.duration_seconds is not None


def test_anomaly_service_flags_spike(db_session) -> None:
    session, hot_camera, _quiet = db_session
    anomaly_service = AnomalyService(AnalyticsRepository(session))

    anomalies = anomaly_service.detect()
    assert len(anomalies) > 0
    assert any(a.kind == "incident_rate_spike" for a in anomalies)
    assert all(0.0 <= a.anomaly_score <= 1.0 for a in anomalies)


def test_recommendation_service_recommends_camera_review(db_session) -> None:
    session, hot_camera, _quiet = db_session
    recommendation_service = RecommendationService(AnalyticsRepository(session))

    recs = recommendation_service.generate(since=datetime.utcnow() - timedelta(days=2))
    assert len(recs) > 0
    assert any(hot_camera.name in r.detail or r.related_camera_id == hot_camera.id for r in recs)


def test_summary_service_builds_narrative(db_session) -> None:
    session, hot_camera, _quiet = db_session
    summary_service = SummaryService(AnalyticsRepository(session))

    summary = summary_service.executive_summary(hours=48)
    assert summary.total_incidents == 6
    assert summary.highest_risk_camera == hot_camera.name
    assert summary.most_frequent_event == "restricted_area"
    assert "Overall risk" in summary.narrative


# ---------------------------------------------------------------------------
# Router-level tests (full stack through FastAPI + dependency override)
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(db_session):
    session, _hot, _quiet = db_session

    def override_get_db():
        yield session

    def override_get_current_user():
        return SimpleNamespace(id=1, username="test-viewer", is_active=True, roles=[SimpleNamespace(name="Viewer")])

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize(
    "path",
    [
        "/analytics/overview",
        "/analytics/trends",
        "/analytics/risk",
        "/analytics/recommendations",
        "/analytics/cameras",
        "/analytics/incidents",
        "/analytics/summary",
        "/analytics/hotspots",
        "/analytics/anomalies",
    ],
)
def test_analytics_endpoints_return_200(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_overview_endpoint_reflects_seeded_data(client: TestClient) -> None:
    response = client.get("/analytics/overview", params={"days": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total_incidents"] == 6
    assert body["total_detections"] == 18


def test_risk_endpoint_ranks_hot_camera_first(client: TestClient, db_session) -> None:
    _session, hot_camera, _quiet = db_session
    response = client.get("/analytics/risk", params={"days": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["by_camera"][0]["camera_id"] == hot_camera.id


def test_anomalies_endpoint_returns_list(client: TestClient) -> None:
    response = client.get("/analytics/anomalies")
    assert response.status_code == 200
    assert "anomalies" in response.json()
