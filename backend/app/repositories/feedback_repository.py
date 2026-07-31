from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate


class FeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, feedback: FeedbackCreate) -> Feedback:
        db_feedback = Feedback(
            customer_id=feedback.customer_id,
            product_name=feedback.product_name,
            feedback_text=feedback.feedback_text,
            sentiment=feedback.sentiment,
        )

        self.db.add(db_feedback)
        self.db.commit()
        self.db.refresh(db_feedback)

        return db_feedback

    def get_all(self) -> list[Feedback]:
        return self.db.query(Feedback).all()

    def exists(self, customer_id, product_name, feedback_text):
        return (
            self.db.query(Feedback)
            .filter(
                Feedback.customer_id == customer_id,
                Feedback.product_name == product_name,
                Feedback.feedback_text == feedback_text,
            )
            .first()
            is not None
        )