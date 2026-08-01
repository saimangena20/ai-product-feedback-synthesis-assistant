from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supporting import AuditLog
from app.models.theme import Theme, ThemeMembership


def _theme(db: Session, theme_id: str) -> Theme:
    theme = db.get(Theme, theme_id)
    if theme is None:
        raise HTTPException(404, detail={"code": "theme_not_found"})
    return theme


def _audit(db: Session, theme: Theme, action: str, details: dict) -> None:
    db.add(AuditLog(id=str(uuid4()), ingest_id=theme.ingest_id, action=action, outcome="success", details=details))


def rename(db: Session, theme_id: str, name: str) -> Theme:
    with db.begin():
        theme = _theme(db, theme_id)
        theme.name = name
        _audit(db, theme, "theme_renamed", {"theme_id": theme_id})
    return theme


def approve(db: Session, theme_id: str) -> Theme:
    with db.begin():
        theme = _theme(db, theme_id)
        theme.review_status, theme.approved_at, theme.rejection_reason = "approved", datetime.now(timezone.utc), None
        _audit(db, theme, "theme_approved", {"theme_id": theme_id, "explicit_user_action": True})
    return theme


def reject(db: Session, theme_id: str, reason: str) -> Theme:
    with db.begin():
        theme = _theme(db, theme_id)
        theme.review_status, theme.rejection_reason = "rejected", reason
        _audit(db, theme, "theme_rejected", {"theme_id": theme_id, "reason": reason})
    return theme


def split(db: Session, theme_id: str, name: str, feedback_ids: list[str], problem_statement: str | None = None) -> Theme:
    with db.begin():
        source = _theme(db, theme_id)
        members = db.scalars(select(ThemeMembership).where(ThemeMembership.theme_id == theme_id, ThemeMembership.feedback_item_id.in_(set(feedback_ids)))).all()
        if len(members) != len(set(feedback_ids)):
            raise HTTPException(422, detail={"code": "invalid_split_members"})
        new_theme = Theme(id=str(uuid4()), ingest_id=source.ingest_id, name=name, problem_statement=problem_statement, review_status="suggested")
        db.add(new_theme)
        for member in members:
            db.add(ThemeMembership(id=str(uuid4()), theme_id=new_theme.id, feedback_item_id=member.feedback_item_id))
            db.delete(member)
        _audit(db, source, "theme_split", {"source_theme_id": source.id, "new_theme_id": new_theme.id, "feedback_item_ids": list(dict.fromkeys(feedback_ids))})
    return new_theme


def merge(db: Session, target_id: str, source_ids: list[str]) -> Theme:
    with db.begin():
        target = _theme(db, target_id)
        sources = [_theme(db, source_id) for source_id in set(source_ids) if source_id != target_id]
        if any(source.ingest_id != target.ingest_id for source in sources):
            raise HTTPException(422, detail={"code": "cross_ingest_merge"})
        existing = set(db.scalars(select(ThemeMembership.feedback_item_id).where(ThemeMembership.theme_id == target_id)).all())
        for source in sources:
            for member in db.scalars(select(ThemeMembership).where(ThemeMembership.theme_id == source.id)).all():
                if member.feedback_item_id not in existing:
                    db.add(ThemeMembership(id=str(uuid4()), theme_id=target_id, feedback_item_id=member.feedback_item_id))
                    existing.add(member.feedback_item_id)
            db.delete(source)
        _audit(db, target, "themes_merged", {"target_theme_id": target_id, "source_theme_ids": [source.id for source in sources]})
    return target
