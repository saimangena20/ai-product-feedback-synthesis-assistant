from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.feedback import FeedbackItem, Ingest, utcnow
from app.models.supporting import AuditLog, Report
from app.models.theme import Theme, ThemeMembership
from app.schemas.report import (
    ReportEvidenceItem,
    ReportListItemResponse,
    ReportReviewSummary,
    ReportSnapshotResponse,
    ReportThemeAnalytics,
    ReportThemeSnapshot,
)
from app.services.analytics_service import theme_analytics


logger = logging.getLogger("app.api")
SCHEMA_VERSION = "2026-08-01"


def _week_points(items: list[FeedbackItem]) -> list[dict[str, object]]:
    analytics = theme_analytics(items)
    return analytics["frequency_over_time"]


def _serialize_feedback_item(item: FeedbackItem) -> ReportEvidenceItem:
    return ReportEvidenceItem(
        feedback_item_id=item.id,
        row_number=item.row_number,
        feedback_text=item.feedback_text,
        source=item.source,
        user_type=item.user_type,
        product_area=item.product_area,
        feedback_date=item.feedback_date,
        rating=item.rating,
    )


def _serialize_theme(theme: Theme) -> ReportThemeSnapshot:
    feedback_items = sorted((membership.feedback_item for membership in theme.memberships), key=lambda item: item.row_number)
    analytics = theme_analytics(feedback_items)
    return ReportThemeSnapshot(
        theme_id=theme.id,
        name=theme.name,
        description=theme.description,
        problem_statement=theme.problem_statement,
        review_status=theme.review_status,
        approved_at=theme.approved_at,
        historical_match_id=theme.historical_match_id,
        historical_commentary=theme.historical_commentary,
        historical_similarity_score=theme.historical_similarity_score,
        advisory_confidence=theme.advisory_confidence,
        supporting_feedback=[_serialize_feedback_item(item) for item in feedback_items],
        analytics=ReportThemeAnalytics(
            feedback_count=analytics["member_count"],
            source_distribution=analytics["distribution_by_source"],
            user_type_distribution=analytics["distribution_by_user_type"],
            frequency_over_time=[{"week_start": point["week_start"], "count": point["count"]} for point in _week_points(feedback_items)],
            recurrence=analytics["recurrence"],
        ),
    )


def _validate_snapshot(snapshot: dict[str, object]) -> ReportSnapshotResponse:
    return ReportSnapshotResponse.model_validate(snapshot)


def build_report_snapshot(db: Session, ingest_id: str, report_id: str | None = None, created_at: datetime | None = None) -> ReportSnapshotResponse:
    ingest = db.get(Ingest, ingest_id)
    if ingest is None:
        raise HTTPException(status_code=404, detail={"code": "ingest_not_found"})

    themes = db.scalars(
        select(Theme)
        .options(selectinload(Theme.memberships).selectinload(ThemeMembership.feedback_item))
        .where(Theme.ingest_id == ingest_id)
        .order_by(Theme.created_at, Theme.id)
    ).all()

    approved = [theme for theme in themes if theme.review_status == "approved"]
    rejected_count = sum(1 for theme in themes if theme.review_status == "rejected")
    unreviewed_count = len(themes) - len(approved) - rejected_count
    if not approved:
        raise HTTPException(status_code=409, detail={"code": "no_approved_themes", "message": "At least one approved theme is required before saving a reviewed synthesis report."})

    snapshot = ReportSnapshotResponse(
        report_id=report_id or str(uuid4()),
        ingest_id=ingest_id,
        created_at=created_at or utcnow(),
        schema_version=SCHEMA_VERSION,
        review_summary=ReportReviewSummary(
            approved_theme_count=len(approved),
            rejected_theme_count=rejected_count,
            unreviewed_theme_count=unreviewed_count,
        ),
        approved_themes=[_serialize_theme(theme) for theme in approved],
    )
    return snapshot


def create_reviewed_report(db: Session, ingest_id: str, request_id: str | None = None) -> ReportSnapshotResponse:
    report_id = str(uuid4())
    created_at = utcnow()
    logger.info("report_create_started", extra={"request_id": request_id, "ingest_id": ingest_id, "report_id": report_id, "action": "report_create", "outcome": "started"})
    snapshot = build_report_snapshot(db, ingest_id, report_id=report_id, created_at=created_at)
    payload = snapshot.model_dump(mode="json")
    try:
        db.commit()
        with db.begin():
            report = Report(id=report_id, ingest_id=ingest_id, status="ready", payload=payload)
            db.add(report)
            db.add(AuditLog(id=str(uuid4()), ingest_id=ingest_id, action="report_created", outcome="success", details={"report_id": report_id, "approved_theme_count": snapshot.review_summary.approved_theme_count, "rejected_theme_count": snapshot.review_summary.rejected_theme_count, "unreviewed_theme_count": snapshot.review_summary.unreviewed_theme_count, "schema_version": snapshot.schema_version}))
    except SQLAlchemyError as exc:
        logger.exception("report_persistence_failed", extra={"request_id": request_id, "ingest_id": ingest_id, "report_id": report_id, "action": "report_create", "outcome": "failure", "error_code": "report_persistence_failed"})
        db.rollback()
        raise HTTPException(status_code=500, detail={"code": "report_persistence_failed", "message": "Could not save the reviewed synthesis report."}) from exc

    logger.info("report_created", extra={"request_id": request_id, "ingest_id": ingest_id, "report_id": report_id, "approved_theme_count": snapshot.review_summary.approved_theme_count, "rejected_theme_count": snapshot.review_summary.rejected_theme_count, "unreviewed_theme_count": snapshot.review_summary.unreviewed_theme_count, "action": "report_create", "outcome": "success"})
    return snapshot


def list_reports(db: Session, ingest_id: str) -> list[ReportListItemResponse]:
    reports = db.scalars(select(Report).where(Report.ingest_id == ingest_id).order_by(desc(Report.created_at), desc(Report.id))).all()
    items: list[ReportListItemResponse] = []
    for report in reports:
        snapshot = _validate_snapshot(report.payload or {})
        items.append(ReportListItemResponse(report_id=snapshot.report_id, ingest_id=snapshot.ingest_id, created_at=snapshot.created_at, schema_version=snapshot.schema_version, review_summary=snapshot.review_summary))
    return items


def get_report(db: Session, report_id: str) -> ReportSnapshotResponse:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"code": "report_not_found"})
    return _validate_snapshot(report.payload or {})