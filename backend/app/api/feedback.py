import logging
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models.historical_theme import HistoricalProductNote
from app.models.supporting import AnalysisJob, AuditLog
from app.models.theme import Theme, ThemeMembership
from app.repositories.feedback_repository import IngestRepository, ThemeRepository
from app.services.ai_service import run_analysis
from app.services.analytics_service import theme_analytics
from app.services.csv_service import CsvValidationError
from app.schemas.report import ReportListItemResponse, ReportSnapshotResponse
from app.services.report_service import create_reviewed_report, get_report, list_reports
from app.services.upload_service import serialize_item, upload_feedback
from app.services import review_service

logger = logging.getLogger("app.api")
router = APIRouter(prefix="/api/v1", tags=["feedback"])


class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1)


class SplitRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    feedback_item_ids: list[str] = Field(min_length=1)
    problem_statement: str | None = Field(default=None, min_length=1)


class MergeRequest(BaseModel):
    source_theme_ids: list[str] = Field(min_length=1)


class HistoricalNoteRequest(BaseModel):
    product_area: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    note: str = Field(min_length=1)


def _serialize_theme_summary(theme: Theme) -> dict[str, object]:
    items = sorted((membership.feedback_item for membership in theme.memberships), key=lambda item: item.row_number)
    metrics = theme_analytics(items)
    return {
        "id": theme.id,
        "ingest_id": theme.ingest_id,
        "name": theme.name,
        "description": theme.description,
        "problem_statement": theme.problem_statement,
        "review_status": theme.review_status,
        "ai_suggested": theme.ai_suggested,
        "advisory_confidence": theme.advisory_confidence,
        "historical_match_id": theme.historical_match_id,
        "historical_commentary": theme.historical_commentary,
        "historical_similarity_score": theme.historical_similarity_score,
        "rejection_reason": theme.rejection_reason,
        "approved_at": theme.approved_at,
        "created_at": theme.created_at,
        "analytics": {
            "feedback_count": metrics["member_count"],
            "source_distribution": metrics["distribution_by_source"],
            "user_type_distribution": metrics["distribution_by_user_type"],
            "frequency_over_time": metrics["frequency_over_time"],
        },
    }


@router.post("/ingests", status_code=status.HTTP_201_CREATED)
@router.post("/feedback/upload", status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def upload_feedback_csv(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, object]:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail={"code": "invalid_file_type", "message": "Only .csv files are allowed."})
    try:
        result = await upload_feedback(file, db)
    except CsvValidationError as exc:
        logger.info("ingest", extra={"request_id": request.state.request_id, "ingest_id": None, "action": "ingest", "outcome": "failure", "error_code": exc.code})
        raise HTTPException(status_code=422, detail={"code": exc.code, "errors": exc.errors}) from exc
    logger.info("ingest", extra={"request_id": request.state.request_id, "ingest_id": result["ingest_id"], "action": "ingest", "outcome": "success", "error_code": None})
    return result


@router.get("/ingests/{ingest_id}")
def ingest_detail(ingest_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    ingest = IngestRepository(db).get(ingest_id)
    if ingest is None:
        raise HTTPException(status_code=404, detail={"code": "ingest_not_found"})
    items = sorted(ingest.feedback_items, key=lambda item: item.row_number)
    return {"ingest_id": ingest.id, "filename": ingest.filename, "status": ingest.status, "job_status": ingest.job_status, "total_rows": ingest.total_rows, "valid_rows": ingest.valid_rows, "preview": [serialize_item(item) for item in items[:10]], "feedback_items": [serialize_item(item) for item in items]}


@router.get("/ingests/{ingest_id}/themes")
def ingest_themes(ingest_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    ingest = IngestRepository(db).get(ingest_id)
    if ingest is None:
        raise HTTPException(status_code=404, detail={"code": "ingest_not_found"})
    themes = db.scalars(
        select(Theme)
        .options(selectinload(Theme.memberships).selectinload(ThemeMembership.feedback_item))
        .where(Theme.ingest_id == ingest_id)
        .order_by(Theme.created_at, Theme.id)
    ).all()
    return {"ingest_id": ingest.id, "themes": [_serialize_theme_summary(theme) for theme in themes]}


@router.post("/ingests/{ingest_id}/reports", response_model=ReportSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_report(ingest_id: str, request: Request, db: Session = Depends(get_db)) -> ReportSnapshotResponse:
    try:
        return create_reviewed_report(db, ingest_id, request.state.request_id)
    except HTTPException:
        raise


@router.get("/ingests/{ingest_id}/reports", response_model=list[ReportListItemResponse])
def ingest_reports(ingest_id: str, db: Session = Depends(get_db)) -> list[ReportListItemResponse]:
    ingest = IngestRepository(db).get(ingest_id)
    if ingest is None:
        raise HTTPException(status_code=404, detail={"code": "ingest_not_found"})
    return list_reports(db, ingest_id)


@router.get("/reports/{report_id}", response_model=ReportSnapshotResponse)
def report_detail(report_id: str, request: Request, db: Session = Depends(get_db)) -> ReportSnapshotResponse:
    try:
        return get_report(db, report_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            logger.warning("report_retrieval_failed", extra={"request_id": request.state.request_id, "report_id": report_id, "action": "report_get", "outcome": "failure", "error_code": "report_not_found"})
        raise


@router.get("/themes/{theme_id}")
def theme_detail(theme_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    theme = ThemeRepository(db).get(theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail={"code": "theme_not_found"})
    items = sorted((membership.feedback_item for membership in theme.memberships), key=lambda item: item.row_number)
    return {"theme_id": theme.id, "ingest_id": theme.ingest_id, "name": theme.name, "description": theme.description, "problem_statement": theme.problem_statement, "review_status": theme.review_status, "ai_suggested": theme.ai_suggested, "advisory_confidence": theme.advisory_confidence, "historical_match": {"note_id": theme.historical_match_id, "commentary": theme.historical_commentary, "similarity_score": theme.historical_similarity_score, "advisory": True} if theme.historical_match_id else None, "approved_at": theme.approved_at, "rejection_reason": theme.rejection_reason, "feedback_items": [serialize_item(item) for item in items], "analytics": theme_analytics(items)}


@router.post("/ingests/{ingest_id}/analysis")
def start_analysis(ingest_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    job = run_analysis(db, ingest_id)
    return {"job_id": job.id, "ingest_id": job.ingest_id, "status": job.status, "attempt_count": job.attempt_count, "error_code": job.error_code, "error_detail": job.error_detail}


@router.post("/analysis-jobs/{job_id}/retry")
def retry_analysis(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(404, detail={"code": "analysis_job_not_found"})
    if job.status != "failed":
        raise HTTPException(409, detail={"code": "analysis_job_not_retryable"})
    db.commit()
    job = run_analysis(db, job.ingest_id, job.id)
    return {"job_id": job.id, "ingest_id": job.ingest_id, "status": job.status, "attempt_count": job.attempt_count, "error_code": job.error_code, "error_detail": job.error_detail}


@router.post("/historical-notes", status_code=201)
def create_historical_note(payload: HistoricalNoteRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    from uuid import uuid4
    note = HistoricalProductNote(id=str(uuid4()), **payload.model_dump())
    with db.begin():
        db.add(note)
    return {"id": note.id}


@router.patch("/themes/{theme_id}/rename")
def rename_theme(theme_id: str, payload: RenameRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return {"theme_id": review_service.rename(db, theme_id, payload.name).id}


@router.post("/themes/{theme_id}/approve")
def approve_theme(theme_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    return {"theme_id": review_service.approve(db, theme_id).id, "review_status": "approved"}


@router.post("/themes/{theme_id}/reject")
def reject_theme(theme_id: str, payload: RejectRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return {"theme_id": review_service.reject(db, theme_id, payload.reason).id, "review_status": "rejected"}


@router.post("/themes/{theme_id}/split", status_code=201)
def split_theme(theme_id: str, payload: SplitRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return {"theme_id": review_service.split(db, theme_id, payload.name, payload.feedback_item_ids, payload.problem_statement).id}


@router.post("/themes/{theme_id}/merge")
def merge_themes(theme_id: str, payload: MergeRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return {"theme_id": review_service.merge(db, theme_id, payload.source_theme_ids).id}


@router.get("/themes/{theme_id}/members")
def list_theme_members(theme_id: str, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    theme = ThemeRepository(db).get(theme_id)
    if theme is None:
        raise HTTPException(404, detail={"code": "theme_not_found"})
    return [serialize_item(member.feedback_item) for member in sorted(theme.memberships, key=lambda membership: membership.feedback_item.row_number)]


@router.get("/themes/{theme_id}/audit")
def theme_audit(theme_id: str, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    theme = ThemeRepository(db).get(theme_id)
    if theme is None:
        raise HTTPException(404, detail={"code": "theme_not_found"})
    logs = db.scalars(select(AuditLog).where(AuditLog.ingest_id == theme.ingest_id).order_by(AuditLog.created_at)).all()
    return [{"id": log.id, "action": log.action, "outcome": log.outcome, "details": log.details, "created_at": log.created_at} for log in logs]
