from sqlalchemy.orm import Session

from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.feedback import FeedbackCreate
from app.services.csv_service import parse_feedback_csv


async def upload_feedback(file, db: Session):
    parsed_data = await parse_feedback_csv(file)

    repository = FeedbackRepository(db)

    saved_records = 0
    duplicate_records = 0

    for record in parsed_data["records"]:

        feedback = FeedbackCreate(
            customer_id=record.get("customer_id"),
            product_name=record["product_name"],
            feedback_text=record["feedback_text"],
            sentiment=record.get("sentiment"),
        )

        # Check whether feedback already exists
        if repository.exists(
            feedback.customer_id,
            feedback.product_name,
            feedback.feedback_text,
        ):
            duplicate_records += 1
            continue

        repository.create(feedback)
        saved_records += 1

    # If every record already exists
    if saved_records == 0:
        return {
            "message": "This dataset has already been uploaded.",
            "records_saved": 0,
            "duplicates_skipped": duplicate_records,
        }

    return {
        "message": "CSV processed successfully.",
        "records_saved": saved_records,
        "duplicates_skipped": duplicate_records,
    }


def get_all_feedback(db):
    repository = FeedbackRepository(db)
    return repository.get_all()