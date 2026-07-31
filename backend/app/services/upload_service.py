import hashlib
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.feedback import CsvSnapshot, FeedbackItem, Ingest
from app.models.supporting import AuditLog
from app.services.csv_service import parse_feedback_csv


def serialize_item(item: FeedbackItem) -> dict[str, object]:
    return {"id": item.id, "row_number": item.row_number, "feedback_text": item.feedback_text, "source": item.source, "user_type": item.user_type, "product_area": item.product_area, "feedback_date": item.feedback_date.isoformat(), "rating": float(item.rating) if item.rating is not None else None, "original_values": item.original_values}


async def upload_feedback(file, db: Session) -> dict[str, object]:
    contents, parsed = await parse_feedback_csv(file)
    ingest_id = str(uuid4())
    records = parsed["records"]
    with db.begin():
        ingest = Ingest(id=ingest_id, filename=file.filename or "upload.csv", total_rows=parsed["total_rows"], valid_rows=len(records))
        db.add(ingest)
        db.add(CsvSnapshot(id=str(uuid4()), ingest_id=ingest_id, content=contents, sha256=hashlib.sha256(contents).hexdigest()))
        items = []
        for record in records:
            item = FeedbackItem(id=str(uuid4()), ingest_id=ingest_id, row_number=record["row_number"], feedback_text=record["feedback_text"], source=record["source"], user_type=record["user_type"], product_area=record["product_area"], feedback_date=record["parsed_date"], rating=record["rating"], original_values=record["original_values"])
            db.add(item)
            items.append(item)
        db.add(AuditLog(id=str(uuid4()), ingest_id=ingest_id, action="ingest_created", outcome="success", details={"total_rows": len(items)}))
    return {"ingest_id": ingest_id, "status": "completed", "job_status": "completed", "total_rows": len(records), "valid_rows": len(records), "preview": [serialize_item(item) for item in items[:10]]}
