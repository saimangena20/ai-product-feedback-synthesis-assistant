from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Ingest(Base):
    __tablename__ = "ingests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    job_status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    snapshot: Mapped["CsvSnapshot"] = relationship(back_populates="ingest", uselist=False, cascade="all, delete-orphan")
    feedback_items: Mapped[list["FeedbackItem"]] = relationship(back_populates="ingest", cascade="all, delete-orphan")
    themes: Mapped[list["Theme"]] = relationship(back_populates="ingest", cascade="all, delete-orphan")


class CsvSnapshot(Base):
    __tablename__ = "csv_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ingest_id: Mapped[str] = mapped_column(ForeignKey("ingests.id", ondelete="CASCADE"), nullable=False, unique=True)
    content: Mapped[bytes] = mapped_column(nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    ingest: Mapped[Ingest] = relationship(back_populates="snapshot")


class FeedbackItem(Base):
    __tablename__ = "feedback_items"
    __table_args__ = (UniqueConstraint("ingest_id", "row_number", name="uq_feedback_items_ingest_row"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ingest_id: Mapped[str] = mapped_column(ForeignKey("ingests.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    user_type: Mapped[str] = mapped_column(String(255), nullable=False)
    product_area: Mapped[str] = mapped_column(String(255), nullable=False)
    feedback_date: Mapped[date] = mapped_column(Date, nullable=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    original_values: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    ingest: Mapped[Ingest] = relationship(back_populates="feedback_items")
    memberships: Mapped[list["ThemeMembership"]] = relationship(back_populates="feedback_item", cascade="all, delete-orphan")
