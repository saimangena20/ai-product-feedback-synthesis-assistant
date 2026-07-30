from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.services.csv_service import parse_feedback_csv


router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("/upload")
async def upload_feedback_csv(file: UploadFile = File(...)) -> dict[str, object]:
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are allowed.",
        )

    return await parse_feedback_csv(file)