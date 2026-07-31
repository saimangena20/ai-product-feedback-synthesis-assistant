from sqlalchemy.orm import Session

from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.feedback import FeedbackCreate
from app.services.csv_service import parse_feedback_csv


async def upload_feedback(file, db: Session):
    parsed_data = await parse_feedback_csv(file)

    repository = FeedbackRepository(db)

    saved_records = 0

    for record in parsed_data["records"]:
        feedback = FeedbackCreate(
            customer_id=record.get("customer_id"),
            product_name=record["product_name"],
            feedback_text=record["feedback_text"],
            sentiment=record.get("sentiment"),
        )

        repository.create(feedback)
        saved_records += 1

    return {
        "message": "CSV uploaded successfully",
        "records_saved": saved_records,
    }