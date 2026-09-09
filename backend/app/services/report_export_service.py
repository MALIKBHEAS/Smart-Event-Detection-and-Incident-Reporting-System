"""Generates downloadable PDF and CSV representations of a Report.

PDF uses reportlab (pure Python, no system-level dependency like
wkhtmltopdf/weasyprint need -- important for the Docker image staying
lightweight). CSV uses the stdlib csv module.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.intelligence.repositories.analytics_repository import AnalyticsRepository
from app.intelligence.services.recommendation_service import RecommendationService
from app.models.report import Report

PROJECT_TITLE = "Sentinel SOC \u2014 Smart Event Detection & Incident Reporting"


def _analytics_context(db: Session, report: Report) -> tuple[list[str], str | None]:
    """Best-effort: pulls a few relevant recommendations and, if the report
    has a camera, that camera's most recent risk info. Analytics failures
    (e.g. an empty/fresh database) must never block report generation, so
    everything here is defensive."""
    recommendations: List[str] = []
    risk_note: str | None = None
    try:
        repo = AnalyticsRepository(db)
        rec_service = RecommendationService(repo)
        for rec in rec_service.generate()[:5]:
            recommendations.append(f"{rec.title}: {rec.detail}")
        if report.camera_id is not None:
            from app.intelligence.services.risk_service import RiskService

            risk_service = RiskService(repo)
            score, level, count = risk_service.score_camera(int(report.camera_id))
            risk_note = f"Camera risk score: {score}/100 ({level}), {count} recent incident(s)."
    except Exception:
        # Analytics is a nice-to-have enrichment for the PDF, not a
        # correctness-critical part of the report itself.
        pass
    return recommendations, risk_note


def generate_report_pdf(report: Report, db: Session) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=18, spaceAfter=4)
    heading_style = ParagraphStyle("SectionHeading", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body_style = styles["BodyText"]
    muted_style = ParagraphStyle("Muted", parent=styles["BodyText"], textColor=colors.grey, fontSize=9)

    story: List[Any] = []

    story.append(Paragraph(PROJECT_TITLE, muted_style))
    story.append(Paragraph(report.title, title_style))
    story.append(
        Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            muted_style,
        )
    )
    story.append(Spacer(1, 10))

    # -- Incident information -----------------------------------------------
    story.append(Paragraph("Incident Information", heading_style))
    info_rows = [
        ["Report ID", str(report.id)],
        ["Status", str(report.status)],
        ["Severity", str(report.severity)],
        ["Incident type", str(report.incident_type or "\u2014")],
        ["Camera", report.camera.name if report.camera else "\u2014"],
        ["Occurred at", report.occurred_at.strftime("%Y-%m-%d %H:%M UTC") if report.occurred_at else "\u2014"],
        ["Resolved at", report.resolved_at.strftime("%Y-%m-%d %H:%M UTC") if report.resolved_at else "\u2014"],
        ["Created at", report.created_at.strftime("%Y-%m-%d %H:%M UTC") if report.created_at else "\u2014"],
    ]
    info_table = Table(info_rows, colWidths=[4 * cm, 11 * cm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
            ]
        )
    )
    story.append(info_table)

    story.append(Paragraph("Summary", heading_style))
    story.append(Paragraph(report.summary or "\u2014", body_style))
    if report.details:
        story.append(Spacer(1, 6))
        story.append(Paragraph(report.details, body_style))

    # -- Event information ----------------------------------------------------
    story.append(Paragraph("Linked Events", heading_style))
    linked_events = list(report.linked_events or [])
    if linked_events:
        event_rows = [["#", "Type", "Severity", "Timestamp"]]
        for event in linked_events[:25]:
            event_rows.append(
                [
                    str(event.id),
                    str(event.type),
                    str(event.severity),
                    event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if event.timestamp else "\u2014",
                ]
            )
        event_table = Table(event_rows, colWidths=[1.5 * cm, 5 * cm, 3.5 * cm, 5 * cm])
        event_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(event_table)
        if len(linked_events) > 25:
            story.append(Paragraph(f"...and {len(linked_events) - 25} more event(s).", muted_style))
    else:
        story.append(Paragraph("No events are currently linked to this report.", body_style))

    # -- Evidence --------------------------------------------------------------
    story.append(Paragraph("Evidence", heading_style))
    attachments: list = list(report.attachments or [])
    if attachments:
        for attachment in attachments:
            if isinstance(attachment, dict):
                label = attachment.get("type", "attachment")
                path = attachment.get("path") or attachment.get("metadata_path") or "\u2014"
                story.append(Paragraph(f"\u2022 {label}: {path}", body_style))
            else:
                story.append(Paragraph(f"\u2022 {attachment}", body_style))
    else:
        story.append(Paragraph("No evidence attachments recorded on this report.", body_style))

    # -- Analytics summary / recommendations ------------------------------------
    recommendations, risk_note = _analytics_context(db, report)
    story.append(Paragraph("Analytics Summary", heading_style))
    story.append(Paragraph(risk_note or "No analytics data available for this camera/window.", body_style))

    story.append(Paragraph("Recommendations", heading_style))
    if recommendations:
        for rec in recommendations:
            story.append(Paragraph(f"\u2022 {rec}", body_style))
    else:
        story.append(Paragraph("No active recommendations at generation time.", body_style))

    doc.build(story)
    return buffer.getvalue()


def generate_report_csv(report: Report) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["field", "value"])
    writer.writerow(["report_id", report.id])
    writer.writerow(["title", report.title])
    writer.writerow(["status", report.status])
    writer.writerow(["severity", report.severity])
    writer.writerow(["incident_type", report.incident_type or ""])
    writer.writerow(["camera", report.camera.name if report.camera else ""])
    writer.writerow(["occurred_at", report.occurred_at.isoformat() if report.occurred_at else ""])
    writer.writerow(["resolved_at", report.resolved_at.isoformat() if report.resolved_at else ""])
    writer.writerow(["created_at", report.created_at.isoformat() if report.created_at else ""])
    writer.writerow(["summary", report.summary])
    writer.writerow([])

    writer.writerow(["event_id", "event_type", "event_severity", "event_timestamp"])
    for event in report.linked_events or []:
        writer.writerow(
            [
                event.id,
                event.type,
                event.severity,
                event.timestamp.isoformat() if event.timestamp else "",
            ]
        )

    return buffer.getvalue()
