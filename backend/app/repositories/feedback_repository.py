from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.feedback import FeedbackItem, Ingest
from app.models.theme import Theme, ThemeMembership


class IngestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, ingest_id: str) -> Ingest | None:
        return self.db.scalar(select(Ingest).options(selectinload(Ingest.feedback_items)).where(Ingest.id == ingest_id))


class ThemeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, theme_id: str) -> Theme | None:
        return self.db.scalar(select(Theme).options(selectinload(Theme.memberships).selectinload(ThemeMembership.feedback_item)).where(Theme.id == theme_id))
