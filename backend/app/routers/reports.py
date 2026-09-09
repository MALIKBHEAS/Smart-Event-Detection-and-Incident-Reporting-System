from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.report import PaginatedReportsResponse, ReportCreate, ReportResponse, ReportUpdate
from app.services.report_export_service import generate_report_csv, generate_report_pdf
from app.services.report_service import ReportNotFoundError, ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

_can_write = require_role("Admin", "Security Operator")


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)


def _to_response(report: Report) -> ReportResponse:
    # ReportResponse.event_count has no backing column on the ORM model (it's
    # a derived value), so from_attributes alone would silently leave it at
    # its default of 0 -- compute it explicitly here.
    response = ReportResponse.model_validate(report)
    response.event_count = len(report.linked_events or [])
    return response


@router.get("", response_model=PaginatedReportsResponse)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    camera_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    service: ReportService = Depends(get_report_service),
    _user: User = Depends(get_current_user),
) -> PaginatedReportsResponse:
    reports, total = service.list_reports(
        page=page,
        page_size=page_size,
        status=status_filter,
        severity=severity,
        camera_id=camera_id,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return PaginatedReportsResponse(
        items=[_to_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    service: ReportService = Depends(get_report_service),
    _user: User = Depends(get_current_user),
) -> ReportResponse:
    try:
        return _to_response(service.get_report(report_id))
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    service: ReportService = Depends(get_report_service),
    _user: User = Depends(_can_write),
) -> ReportResponse:
    report = service.create_report(payload)
    return _to_response(report)


@router.put("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    service: ReportService = Depends(get_report_service),
    _user: User = Depends(_can_write),
) -> ReportResponse:
    try:
        return _to_response(service.update_report(report_id, payload))
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: int,
    service: ReportService = Depends(get_report_service),
    _user: User = Depends(_can_write),
) -> None:
    try:
        service.delete_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{report_id}/download/pdf")
def download_report_pdf(
    report_id: int,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
    _user: User = Depends(get_current_user),
) -> Response:
    try:
        report = service.get_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    pdf_bytes = generate_report_pdf(report, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report_id}.pdf"'},
    )


@router.get("/{report_id}/download/csv")
def download_report_csv(
    report_id: int,
    service: ReportService = Depends(get_report_service),
    _user: User = Depends(get_current_user),
) -> Response:
    try:
        report = service.get_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    csv_text = generate_report_csv(report)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report-{report_id}.csv"'},
    )
