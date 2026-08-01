"""Evidence-first Gemini suggestions. Deterministic analytics are never sent to or accepted from the provider."""
import logging
import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.feedback import FeedbackItem, Ingest
from app.models.historical_theme import HistoricalProductNote
from app.models.supporting import AnalysisJob, AuditLog
from app.models.theme import Theme, ThemeMembership


logger = logging.getLogger("app.services.ai")


class SuggestedTheme(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suggested_theme_label: str = Field(min_length=1, max_length=255)
    suggested_problem_statement: str = Field(min_length=1)
    cited_feedback_ids: list[str] = Field(min_length=1)
    historical_match_id: str | None = None
    historical_commentary: str | None = None
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    advisory_confidence: float | None = Field(default=None, ge=0, le=1)


class SuggestionEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    themes: list[SuggestedTheme] = Field(default_factory=list)


class SuggestedThemePayload(TypedDict):
    suggested_theme_label: str
    suggested_problem_statement: str
    cited_feedback_ids: list[str]
    historical_match_id: str | None
    historical_commentary: str | None
    similarity_score: float | None
    advisory_confidence: float | None


class SuggestionEnvelopePayload(TypedDict):
    themes: list[SuggestedThemePayload]


class AnalysisFailure(Exception):
    def __init__(self, code: str, detail: str):
        self.code, self.detail = code, detail


def _prompt(items: list[FeedbackItem], notes: list[HistoricalProductNote]) -> str:
    evidence = [{"id": item.id, "text": item.feedback_text, "source": item.source, "user_type": item.user_type, "product_area": item.product_area, "date": item.feedback_date.isoformat()} for item in items]
    historical = [{"id": note.id, "product_area": note.product_area, "title": note.title, "note": note.note} for note in notes]
    return """You are an evidence suggestion assistant. Return application/json only with {themes:[...]}. Do not wrap the response in markdown fences or add commentary. Each theme must include suggested_theme_label, suggested_problem_statement, cited_feedback_ids, and optional historical_match_id, historical_commentary, similarity_score, advisory_confidence. Cite only supplied IDs. Never calculate, return, imply, or claim counts, distributions, trends, recurrence, priorities, or roadmap recommendations. Do not approve themes. Historical similarity is advisory, not factual.\nFeedback items:\n""" + json.dumps(evidence) + "\nHistorical product notes:\n" + json.dumps(historical)


def generate_ai_json(prompt: str) -> str:
    if not settings.gemini_api_key:
        raise AnalysisFailure("provider_not_configured", "GEMINI_API_KEY is required to run analysis.")
    try:
        import google.generativeai as genai
        from google.generativeai import types as genai_types

        genai.configure(api_key=settings.gemini_api_key)
        response = genai.GenerativeModel(settings.gemini_model).generate_content(
            prompt,
            generation_config=genai_types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=SuggestionEnvelopePayload,
                temperature=0.0,
            ),
        )
        return response.text
    except AnalysisFailure:
        raise
    except Exception as exc:
        raise AnalysisFailure("provider_failure", "The Gemini provider did not return a usable response.") from exc


def _parse(raw: str) -> SuggestionEnvelope:
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        return SuggestionEnvelope.model_validate_json(cleaned)
    except (ValueError, ValidationError, IndexError) as exc:
        logger.warning("provider_json_validation_failed", extra={"error_code": "malformed_provider_json", "response_length": len(raw), "validation_error": str(exc)})
        raise AnalysisFailure("malformed_provider_json", "Provider output did not match the required evidence JSON schema.") from exc


def run_analysis(db: Session, ingest_id: str, job_id: str | None = None) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id) if job_id else None
    if job is None:
        job = AnalysisJob(id=str(uuid4()), ingest_id=ingest_id, status="queued")
        db.add(job)
        db.commit()
    else:
        db.commit()
    try:
        with db.begin():
            job.status, job.error_code, job.error_detail = "running", None, None
            job.attempt_count += 1
        ingest = db.get(Ingest, ingest_id)
        if ingest is None:
            raise AnalysisFailure("ingest_not_found", "The requested ingest does not exist.")
        items = db.scalars(select(FeedbackItem).where(FeedbackItem.ingest_id == ingest_id).order_by(FeedbackItem.row_number)).all()
        notes = db.scalars(select(HistoricalProductNote).where(HistoricalProductNote.product_area.in_({item.product_area for item in items}))).all() if items else []
        suggestions = _parse(generate_ai_json(_prompt(items, notes)))
        valid_ids, valid_note_ids = {item.id for item in items}, {note.id for note in notes}
        for suggestion in suggestions.themes:
            if not set(suggestion.cited_feedback_ids).issubset(valid_ids):
                raise AnalysisFailure("invalid_citations", "One or more cited feedback IDs do not belong to this ingest.")
            if suggestion.historical_match_id and suggestion.historical_match_id not in valid_note_ids:
                raise AnalysisFailure("invalid_historical_match", "Suggested historical note does not apply to this ingest.")
        db.commit()  # End the read transaction before the atomic theme/job write.
        with db.begin():
            existing_themes = db.scalars(select(Theme).where(Theme.ingest_id == ingest_id).options(selectinload(Theme.memberships))).all()
            existing_signatures = {frozenset(membership.feedback_item_id for membership in theme.memberships): theme for theme in existing_themes}
            for suggestion in suggestions.themes:
                citation_signature = frozenset(dict.fromkeys(suggestion.cited_feedback_ids))
                existing_theme = existing_signatures.get(citation_signature)
                if existing_theme is not None:
                    if existing_theme.problem_statement is None:
                        existing_theme.problem_statement = suggestion.suggested_problem_statement
                    continue
                theme = Theme(id=str(uuid4()), ingest_id=ingest_id, name=suggestion.suggested_theme_label, description=suggestion.suggested_problem_statement, problem_statement=suggestion.suggested_problem_statement, ai_suggested=True, review_status="suggested", advisory_confidence=suggestion.advisory_confidence, historical_match_id=suggestion.historical_match_id, historical_commentary=suggestion.historical_commentary, historical_similarity_score=suggestion.similarity_score)
                db.add(theme)
                for feedback_id in dict.fromkeys(suggestion.cited_feedback_ids):
                    db.add(ThemeMembership(id=str(uuid4()), theme_id=theme.id, feedback_item_id=feedback_id))
            job.status, job.completed_at = "completed", datetime.now(timezone.utc)
            db.add(AuditLog(id=str(uuid4()), ingest_id=ingest_id, action="analysis_completed", outcome="success", details={"job_id": job.id, "themes_created": len(suggestions.themes)}))
        return job
    except AnalysisFailure as exc:
        db.rollback()
        with db.begin():
            job.status, job.error_code, job.error_detail = "failed", exc.code, exc.detail
            job.completed_at = datetime.now(timezone.utc)
            db.add(AuditLog(id=str(uuid4()), ingest_id=ingest_id, action="analysis_completed", outcome="failure", details={"job_id": job.id, "error_code": exc.code}))
        return job
