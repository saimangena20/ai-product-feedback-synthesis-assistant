from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    customer_id: str | None = None
    product_name: str
    feedback_text: str
    sentiment: str | None = None