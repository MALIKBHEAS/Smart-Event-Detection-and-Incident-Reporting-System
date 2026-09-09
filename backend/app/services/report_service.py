from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.report import Report
from app.notifications.manager import connection_manager
from app.notifications.repository import NotificationRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.settings_repository import SettingsRepository
from app.schemas.report import ReportCreate, ReportUpdate

logger = logging.getLogger(__name__)


class ReportNotFoundError(Exception):
    pass


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReportRepository(db)

    def list_reports(
        self,
        *,
        page: int,
        page_size: int,
        status: Optional[str],
        severity: Optional[str],
        camera_id: Optional[int],
        search: Optional[str],
        sort_by: str,
        sort_dir: str,
    ) -> Tuple[List[Report], int]:
        return self.repo.list(
            page=page,
            page_size=page_size,
            status=status,
            severity=severity,
            camera_id=camera_id,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    def get_report(self, report_id: int) -> Report:
        report = self.repo.get(report_id)
        if report is None:
            raise ReportNotFoundError(f"Report {report_id} not found")
        return report

    def create_report(self, payload: ReportCreate) -> Report:
        report = Report(**payload.model_dump())
        created = self.repo.create(report)
        self._notify_incident_created(created)
        return created

    def update_report(self, report_id: int, payload: ReportUpdate) -> Report:
        report = self.get_report(report_id)
        previous_status = report.status
        updated = self.repo.update(report, **payload.model_dump(exclude_unset=True))
        if payload.status is not None and payload.status != previous_status:
            self._notify_status_changed(updated, previous_status)
        return updated

    def _notify_incident_created(self, report: Report) -> None:
        try:
            if not SettingsRepository(self.db).get().notify_on_new_incident:
                return
            record = NotificationRepository(self.db).create(
                type="new_incident",
                message=f"New incident: {report.title} ({report.severity})",
                severity=str(report.severity),
                related_type="report",
                related_id=int(report.id),
            )
            connection_manager.broadcast_threadsafe(
                {
                    "id": record.id,
                    "type": record.type,
                    "message": record.message,
                    "severity": record.severity,
                    "related_type": record.related_type,
                    "related_id": record.related_id,
                }
            )
        except Exception:
            # Notifications are best-effort -- never let a broadcast failure
            # break incident creation itself.
            logger.exception("Failed to create/broadcast new_incident notification for report %s", report.id)

    def _notify_status_changed(self, report: Report, previous_status: object) -> None:
        try:
            record = NotificationRepository(self.db).create(
                type="incident_updated",
                message=f"Incident '{report.title}' changed from {previous_status} to {report.status}",
                severity=str(report.severity),
                related_type="report",
                related_id=int(report.id),
            )
            connection_manager.broadcast_threadsafe(
                {
                    "id": record.id,
                    "type": record.type,
                    "message": record.message,
                    "severity": record.severity,
                    "related_type": record.related_type,
                    "related_id": record.related_id,
                }
            )
        except Exception:
            logger.exception("Failed to create/broadcast incident_updated notification for report %s", report.id)

    def delete_report(self, report_id: int) -> None:
        report = self.get_report(report_id)
        self.repo.delete(report)
