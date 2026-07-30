import csv
import io

from fastapi import HTTPException, UploadFile, status

REQUIRED_COLUMNS = {"customer_id", "product_name", "feedback_text"}


async def parse_feedback_csv(file: UploadFile) -> dict[str, object]:
    contents = await file.read()
    text_stream = io.StringIO(contents.decode("utf-8-sig"))

    reader = csv.DictReader(text_stream)

    fieldnames = {
        name.strip().lower()
        for name in (reader.fieldnames or [])
    }

    missing_columns = REQUIRED_COLUMNS.difference(fieldnames)

    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(sorted(missing_columns))}",
        )

    records = []

    for row in reader:
        clean_row = {
            key.strip(): value.strip().strip('"') if value else value
            for key, value in row.items()
        }
        records.append(clean_row)

    return {
        "total_records": len(records),
        "records": records,
    }