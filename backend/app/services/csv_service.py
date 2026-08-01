import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fastapi import UploadFile

REQUIRED_HEADERS = {
    "feedback text": "feedback_text",
    "source": "source",
    "user type": "user_type",
    "product area": "product_area",
    "date": "feedback_date",
}
OPTIONAL_HEADERS = {"rating": "rating"}

HEADER_ALIASES: dict[str, str] = {
    "feedback text": "feedback text",
    "feedback": "feedback text",
    "review": "feedback text",
    "comment": "feedback text",
    "comments": "feedback text",
    "customer feedback": "feedback text",
    "customer review": "feedback text",
    "user feedback": "feedback text",
    "message": "feedback text",
    "issue": "feedback text",
    "source": "source",
    "channel": "source",
    "platform": "source",
    "origin": "source",
    "feedback source": "source",
    "user type": "user type",
    "customer type": "user type",
    "customer segment": "user type",
    "user segment": "user type",
    "plan": "user type",
    "tier": "user type",
    "account type": "user type",
    "product area": "product area",
    "feature": "product area",
    "module": "product area",
    "category": "product area",
    "component": "product area",
    "product feature": "product area",
    "area": "product area",
    "date": "date",
    "feedback date": "date",
    "created at": "date",
    "created date": "date",
    "submitted at": "date",
    "submitted date": "date",
    "timestamp": "date",
    "rating": "rating",
    "stars": "rating",
    "score": "rating",
    "review score": "rating",
    "satisfaction score": "rating",
}


class CsvValidationError(Exception):
    def __init__(self, code: str, errors: list[dict[str, object]]):
        self.code = code
        self.errors = errors


def _header(value: str | None) -> str:
    normalized = (value or "").strip().casefold()
    normalized = re.sub(r"[\s_-]+", " ", normalized)
    return normalized


def _canonical_header(value: str | None) -> str | None:
    return HEADER_ALIASES.get(_header(value))


def _build_header_map(headers: list[str]) -> dict[str, str]:
    matched_headers: dict[str, list[str]] = {display: [] for display in (*REQUIRED_HEADERS.keys(), *OPTIONAL_HEADERS.keys())}
    for header in headers:
        canonical = _canonical_header(header)
        if canonical is None:
            continue
        matched_headers[canonical].append(header)
    ambiguous = [
        {
            "row": 1,
            "column": display,
            "message": f'Multiple uploaded columns map to "{display}".',
            "conflicting_headers": values,
        }
        for display, values in matched_headers.items()
        if len(values) > 1
    ]
    if ambiguous:
        raise CsvValidationError("ambiguous_headers", ambiguous)
    return {display: matched_headers[display][0] for display in REQUIRED_HEADERS if matched_headers[display]} | {
        display: matched_headers[display][0] for display in OPTIONAL_HEADERS if matched_headers[display]
    }


def _parse_date(value: str | None) -> date:
    cleaned = (value or "").strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            pass
    raise ValueError("unparseable date")


def parse_csv_bytes(contents: bytes) -> dict[str, object]:
    try:
        text_stream = io.StringIO(contents.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise CsvValidationError("invalid_encoding", [{"row": 1, "message": "CSV must be UTF-8 encoded."}]) from exc
    reader = csv.DictReader(text_stream)
    headers = reader.fieldnames or []
    header_map = _build_header_map(headers)
    missing = [display for display in REQUIRED_HEADERS if display not in header_map]
    if missing:
        raise CsvValidationError("missing_headers", [{"row": 1, "column": name, "message": "Required header is missing."} for name in missing])

    records: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for row_number, raw_row in enumerate(reader, start=2):
        original_values = {key: value for key, value in raw_row.items() if key is not None}
        values = {internal: raw_row.get(header_map[display]) for display, internal in REQUIRED_HEADERS.items()}
        rating_value = raw_row.get(header_map["rating"]) if "rating" in header_map else None
        for display, internal in REQUIRED_HEADERS.items():
            if internal == "feedback_date":
                continue
            if not isinstance(values[internal], str) or not values[internal].strip():
                errors.append({"row": row_number, "column": display, "message": "Required text field must be non-empty."})
        parsed_date: date | None = None
        try:
            parsed_date = _parse_date(values["feedback_date"])
        except (TypeError, ValueError):
            errors.append({"row": row_number, "column": "date", "message": "Date must be parseable (for example YYYY-MM-DD or MM/DD/YYYY)."})
        parsed_rating: Decimal | None = None
        if rating_value is not None and rating_value.strip():
            try:
                parsed_rating = Decimal(rating_value.strip())
            except (InvalidOperation, ValueError):
                errors.append({"row": row_number, "column": "rating", "message": "Rating must be numeric when present."})
        records.append({**values, "rating": parsed_rating, "parsed_date": parsed_date, "row_number": row_number, "original_values": original_values})
    if errors:
        raise CsvValidationError("invalid_rows", errors)
    return {"total_rows": len(records), "records": records}


async def parse_feedback_csv(file: UploadFile) -> tuple[bytes, dict[str, object]]:
    contents = await file.read()
    return contents, parse_csv_bytes(contents)
