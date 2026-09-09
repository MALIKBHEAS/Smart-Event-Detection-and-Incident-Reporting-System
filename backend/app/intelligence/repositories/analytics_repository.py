"""Aggregation-query repository for the Intelligence & Analytics module.

Everything here is read-only and computed via SQL aggregation (COUNT/GROUP
BY) against the existing `events`, `reports`, and `cameras` tables -- no new
tables, and no loading of full incident sets into memory. Date bucketing is
dialect-aware so this works against both the SQLite dev database and
Postgres in production.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence, Tuple, cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.camera import Camera
from app.models.event import Event
from app.models.report import Report


def _is_postgres(session: Session) -> bool:
    return bool(session.bind is not None and session.bind.dialect.name == "postgresql")


def _day_bucket(session: Session, column):
    if _is_postgres(session):
        return func.to_char(column, "YYYY-MM-DD")
    return func.strftime("%Y-%m-%d", column)


def _week_bucket(session: Session, column):
    if _is_postgres(session):
        return func.to_char(column, "IYYY-IW")
    return func.strftime("%Y-%W", column)


def _month_bucket(session: Session, column):
    if _is_postgres(session):
        return func.to_char(column, "YYYY-MM")
    return func.strftime("%Y-%m", column)


def _hour_bucket(session: Session, column):
    if _is_postgres(session):
        return func.to_char(column, "HH24")
    return func.strftime("%H", column)


class AnalyticsRepository:
    """Read-only aggregation queries over Event/Report/Camera."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # -- counts ---------------------------------------------------------

    def total_events(self, since: Optional[datetime] = None) -> int:
        query = self.session.query(func.count(Event.id))
        if since is not None:
            query = query.filter(Event.timestamp >= since)
        return int(query.scalar() or 0)

    def total_incidents(self, since: Optional[datetime] = None) -> int:
        query = self.session.query(func.count(Report.id))
        if since is not None:
            query = query.filter(Report.created_at >= since)
        return int(query.scalar() or 0)

    # -- grouped counts ---------------------------------------------------

    def incidents_by_camera(self, since: Optional[datetime] = None) -> List[Tuple[Optional[int], Optional[str], int]]:
        query = (
            self.session.query(Report.camera_id, Camera.name, func.count(Report.id))
            .outerjoin(Camera, Camera.id == Report.camera_id)
            .group_by(Report.camera_id, Camera.name)
            .order_by(func.count(Report.id).desc())
        )
        if since is not None:
            query = query.filter(Report.created_at >= since)
        return [(row[0], row[1], int(row[2])) for row in query.all()]

    def incidents_by_bucket(self, granularity: str, since: Optional[datetime] = None, limit: int = 60) -> List[Tuple[str, int]]:
        bucket_fn = {"day": _day_bucket, "week": _week_bucket, "month": _month_bucket}[granularity]
        bucket = bucket_fn(self.session, Report.created_at)
        query = self.session.query(bucket.label("bucket"), func.count(Report.id)).group_by(bucket).order_by(bucket.desc())
        if since is not None:
            query = query.filter(Report.created_at >= since)
        rows = query.limit(limit).all()
        return [(str(row[0]), int(row[1])) for row in rows][::-1]

    def incidents_by_field(self, field: str, since: Optional[datetime] = None) -> List[Tuple[Optional[str], int]]:
        column = getattr(Report, field)
        query = self.session.query(column, func.count(Report.id)).group_by(column).order_by(func.count(Report.id).desc())
        if since is not None:
            query = query.filter(Report.created_at >= since)
        return [(row[0], int(row[1])) for row in query.all()]

    def events_by_hour(self, since: Optional[datetime] = None) -> List[Tuple[str, int]]:
        bucket = _hour_bucket(self.session, Event.timestamp)
        query = self.session.query(bucket.label("hour"), func.count(Event.id)).group_by(bucket).order_by(bucket)
        if since is not None:
            query = query.filter(Event.timestamp >= since)
        return [(str(row[0]), int(row[1])) for row in query.all()]

    def incidents_by_type_and_camera(self, since: Optional[datetime] = None) -> List[Tuple[Optional[str], Optional[int], Optional[str], int]]:
        query = (
            self.session.query(Report.incident_type, Report.camera_id, Camera.name, func.count(Report.id))
            .outerjoin(Camera, Camera.id == Report.camera_id)
            .group_by(Report.incident_type, Report.camera_id, Camera.name)
            .order_by(func.count(Report.id).desc())
        )
        if since is not None:
            query = query.filter(Report.created_at >= since)
        return [(row[0], row[1], row[2], int(row[3])) for row in query.all()]

    # -- raw rows (bounded) -----------------------------------------------

    def recent_reports(self, since: Optional[datetime] = None, limit: int = 500) -> Sequence[Report]:
        """Bounded fetch of recent Report rows (for clustering/pattern logic
        that needs row-level detail, e.g. per-incident event counts)."""
        query = self.session.query(Report).order_by(Report.created_at.desc())
        if since is not None:
            query = query.filter(Report.created_at >= since)
        return query.limit(limit).all()

    def event_count_for_report(self, report_id: int) -> int:
        return int(self.session.query(func.count(Event.id)).filter(Event.report_id == report_id).scalar() or 0)

    def event_time_span_for_report(self, report_id: int) -> Tuple[Optional[datetime], Optional[datetime]]:
        row = (
            self.session.query(func.min(Event.timestamp), func.max(Event.timestamp))
            .filter(Event.report_id == report_id)
            .one()
        )
        return row[0], row[1]

    def recent_event_payloads_for_camera(self, camera_id: int, since: Optional[datetime], limit: int = 200) -> List[dict]:
        """Bounded (per-camera, windowed, limited) fetch of raw payloads --
        used only for best-effort confidence averaging; payload contents
        aren't guaranteed to include a numeric score so this stays small."""
        query = self.session.query(Event.payload).filter(Event.camera_id == camera_id)
        if since is not None:
            query = query.filter(Event.timestamp >= since)
        rows = query.order_by(Event.timestamp.desc()).limit(limit).all()
        return [row[0] for row in rows if row[0]]

    def last_incident_at_for_camera(self, camera_id: int) -> Optional[datetime]:
        result = self.session.query(func.max(Report.created_at)).filter(Report.camera_id == camera_id).scalar()
        return cast(Optional[datetime], result)

    def cameras(self) -> Sequence[Camera]:
        return self.session.query(Camera).order_by(Camera.name).all()
