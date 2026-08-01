from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ReportEvidenceItem(BaseModel):
    feedback_item_id: str
    row_number: int
    feedback_text: str
    source: str
    user_type: str
    product_area: str
    feedback_date: date
    rating: Decimal | None = None


class ReportFrequencyPoint(BaseModel):
    week_start: str
    count: int


class ReportThemeAnalytics(BaseModel):
    feedback_count: int
    source_distribution: dict[str, int]
    user_type_distribution: dict[str, int]
    frequency_over_time: list[ReportFrequencyPoint]
    recurrence: str


class ReportThemeSnapshot(BaseModel):
    theme_id: str
    name: str
    description: str | None = None
    problem_statement: str | None = None
    review_status: str
    approved_at: datetime | None = None
    historical_match_id: str | None = None
    historical_commentary: str | None = None
    historical_similarity_score: float | None = None
    advisory_confidence: float | None = None
    supporting_feedback: list[ReportEvidenceItem]
    analytics: ReportThemeAnalytics


class ReportReviewSummary(BaseModel):
    approved_theme_count: int
    rejected_theme_count: int
    unreviewed_theme_count: int


class ReportSnapshotResponse(BaseModel):
    report_id: str
    ingest_id: str
    created_at: datetime
    schema_version: str
    review_summary: ReportReviewSummary
    approved_themes: list[ReportThemeSnapshot]


class ReportListItemResponse(BaseModel):
    report_id: str
    ingest_id: str
    created_at: datetime
    schema_version: str
    review_summary: ReportReviewSummary