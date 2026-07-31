import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.feedback_repository import IngestRepository, ThemeRepository
from app.services.analytics_service import theme_analytics
from app.services.csv_service import CsvValidationError
from app.services.upload_service import serialize_item, upload_feedback

logger = logging.getLogger("app.api")
router = APIRouter(prefix="/api/v1", tags=["feedback"])


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


@router.get("/themes/{theme_id}")
def theme_detail(theme_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    theme = ThemeRepository(db).get(theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail={"code": "theme_not_found"})
    items = sorted((membership.feedback_item for membership in theme.memberships), key=lambda item: item.row_number)
    return {"theme_id": theme.id, "ingest_id": theme.ingest_id, "name": theme.name, "description": theme.description, "feedback_items": [serialize_item(item) for item in items], "analytics": theme_analytics(items)}
