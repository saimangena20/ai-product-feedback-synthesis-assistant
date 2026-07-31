from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class FeedbackItemResponse(BaseModel):
    id: str
    row_number: int
    feedback_text: str
    source: str
    user_type: str
    product_area: str
    feedback_date: date
    rating: Decimal | None = None
    original_values: dict[str, object]
