from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.feedback import utcnow


class Theme(Base):
    __tablename__ = "themes"
    __table_args__ = (UniqueConstraint("ingest_id", "name", name="uq_themes_ingest_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ingest_id: Mapped[str] = mapped_column(ForeignKey("ingests.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    problem_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="suggested")
    ai_suggested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    advisory_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    historical_match_id: Mapped[str | None] = mapped_column(ForeignKey("historical_product_notes.id", ondelete="SET NULL"), nullable=True)
    historical_commentary: Mapped[str | None] = mapped_column(Text, nullable=True)
    historical_similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    ingest = relationship("Ingest", back_populates="themes")
    memberships: Mapped[list["ThemeMembership"]] = relationship(back_populates="theme", cascade="all, delete-orphan")


class ThemeMembership(Base):
    __tablename__ = "theme_memberships"
    __table_args__ = (UniqueConstraint("theme_id", "feedback_item_id", name="uq_theme_membership"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    theme_id: Mapped[str] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_item_id: Mapped[str] = mapped_column(ForeignKey("feedback_items.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    theme: Mapped[Theme] = relationship(back_populates="memberships")
    feedback_item = relationship("FeedbackItem", back_populates="memberships")
