from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.feedback import utcnow


class HistoricalTheme(Base):
    __tablename__ = "historical_themes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    theme_name: Mapped[str] = mapped_column(String(255), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
