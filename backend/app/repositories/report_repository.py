"""Repository for Report persistence: CRUD, filtering, search, pagination,
sorting. Session-injected (mirrors CameraRepository's style, since reports
are read/written within a single FastAPI request lifecycle like cameras --
unlike EventRepository, which self-manages sessions because it's called
from background worker threads)."""
from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.models.report import Report

SORTABLE_FIELDS = {
    "created_at": Report.created_at,
    "updated_at": Report.updated_at,
    "occurred_at": Report.occurred_at,
    "severity": Report.severity,
    "status": Report.status,
    "title": Report.title,
}


class ReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, report: Report) -> Report:
        self._session.add(report)
        self._session.commit()
        self._session.refresh(report)
        return report

    def get(self, report_id: int) -> Optional[Report]:
        return self._session.get(Report, report_id)

    def update(self, report: Report, **fields: object) -> Report:
        for key, value in fields.items():
            if value is not None:
                setattr(report, key, value)
        self._session.add(report)
        self._session.commit()
        self._session.refresh(report)
        return report

    def delete(self, report: Report) -> None:
        self._session.delete(report)
        self._session.commit()

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        camera_id: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> Tuple[List[Report], int]:
        query = self._session.query(Report)

        if status:
            query = query.filter(Report.status == status)
        if severity:
            query = query.filter(Report.severity == severity)
        if camera_id is not None:
            query = query.filter(Report.camera_id == camera_id)
        if search:
            like = f"%{search}%"
            query = query.filter(or_(Report.title.ilike(like), Report.summary.ilike(like)))

        total = query.count()

        sort_column = SORTABLE_FIELDS.get(sort_by, Report.created_at)
        order_fn = asc if sort_dir == "asc" else desc
        query = query.order_by(order_fn(sort_column))  # type: ignore[arg-type]

        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        return rows, total
