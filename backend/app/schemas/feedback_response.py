from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedbackResponse(BaseModel):
    id: int
    customer_id: str | None
    product_name: str
    feedback_text: str
    sentiment: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)