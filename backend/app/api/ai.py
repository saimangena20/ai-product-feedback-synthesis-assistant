from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.ai_service import analyze_feedback

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["AI"],
)


@router.get("/analyze")
def analyze(db: Session = Depends(get_db)):
    return analyze_feedback(db)