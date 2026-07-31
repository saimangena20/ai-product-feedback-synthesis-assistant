from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.upload_service import upload_feedback


router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("/upload")
async def upload_feedback_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are allowed.",
        )

    return await upload_feedback(file, db)