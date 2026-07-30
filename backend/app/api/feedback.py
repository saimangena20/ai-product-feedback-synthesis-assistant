from fastapi import APIRouter, File, HTTPException, UploadFile, status


router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("/upload")
async def upload_feedback_csv(file: UploadFile = File(...)) -> dict[str, str]:
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are allowed.",
        )

    return {
        "filename": filename,
        "message": "CSV received successfully",
    }