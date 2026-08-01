from datetime import date, datetime, timezone
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.feedback import FeedbackItem, Ingest
from app.models.historical_theme import HistoricalProductNote
from app.models.supporting import AuditLog, Report
from app.models.theme import Theme, ThemeMembership


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _seed_reviewed_ingest(session):
    ingest = Ingest(id=str(uuid4()), filename="reviewed.csv", total_rows=4, valid_rows=4)
    session.add(ingest)
    note = HistoricalProductNote(id=str(uuid4()), product_area="search", title="Battery note", note="Historically similar battery issue.")
    session.add(note)
    items = [
        FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=2, feedback_text="Battery drains after update", source="email", user_type="admin", product_area="search", feedback_date=date(2026, 7, 21), rating=None, original_values={"Feedback Text": "Battery drains after update"}),
        FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=3, feedback_text="Battery is worse after patch", source="web", user_type="member", product_area="search", feedback_date=date(2026, 7, 29), rating=None, original_values={"Feedback Text": "Battery is worse after patch"}),
        FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=4, feedback_text="Rejected item", source="web", user_type="member", product_area="search", feedback_date=date(2026, 7, 30), rating=None, original_values={"Feedback Text": "Rejected item"}),
        FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=5, feedback_text="Unreviewed item", source="chat", user_type="guest", product_area="search", feedback_date=date(2026, 7, 31), rating=None, original_values={"Feedback Text": "Unreviewed item"}),
    ]
    session.add_all(items)
    approved = Theme(id=str(uuid4()), ingest_id=ingest.id, name="Battery Drain After Update", description="Battery drain after the latest update", problem_statement="Users report battery drain after the latest update.", review_status="approved", ai_suggested=True, advisory_confidence=0.91, historical_match_id=note.id, historical_commentary="Matches a known historical battery issue.", historical_similarity_score=0.66, approved_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
    rejected = Theme(id=str(uuid4()), ingest_id=ingest.id, name="Rejected Theme", description="Rejected description", problem_statement="Rejected problem statement", review_status="rejected", ai_suggested=True, rejection_reason="Duplicate of another theme")
    suggested = Theme(id=str(uuid4()), ingest_id=ingest.id, name="Unreviewed Theme", description="Suggested description", problem_statement="Suggested problem statement", review_status="suggested", ai_suggested=True)
    session.add_all([approved, rejected, suggested])
    session.add_all([
        ThemeMembership(id=str(uuid4()), theme_id=approved.id, feedback_item_id=items[0].id),
        ThemeMembership(id=str(uuid4()), theme_id=approved.id, feedback_item_id=items[1].id),
        ThemeMembership(id=str(uuid4()), theme_id=rejected.id, feedback_item_id=items[2].id),
        ThemeMembership(id=str(uuid4()), theme_id=suggested.id, feedback_item_id=items[3].id),
    ])
    session.commit()
    return ingest, approved, rejected, suggested, items, note


def ingest(client):
    csv_text = "Feedback Text,Source,User Type,Product Area,Date\nBattery drains,email,admin,search,2026-07-28\nBattery drains again,web,member,search,2026-07-29\n"
    return client.post("/api/v1/ingests", files={"file": ("evidence.csv", BytesIO(csv_text.encode()), "text/csv")}).json()


def _ai_json_response(item_ids, problem_statement, note_id=None):
    theme = {"suggested_theme_label": "Battery Drain After Update", "suggested_problem_statement": problem_statement, "cited_feedback_ids": item_ids, "advisory_confidence": 0.91}
    if note_id:
        theme.update({"historical_match_id": note_id, "historical_commentary": "Matches a known historical battery issue.", "similarity_score": 0.66})
    return '{"themes": [' + __import__("json").dumps(theme) + ']}'


def test_save_and_retrieve_reviewed_report_snapshot(client):
    session = client[1]()
    ingest, approved, rejected, suggested, items, note = _seed_reviewed_ingest(session)
    session.close()

    response = client[0].post(f"/api/v1/ingests/{ingest.id}/reports")
    assert response.status_code == 201
    body = response.json()
    assert body["ingest_id"] == ingest.id
    assert body["schema_version"] == "2026-08-01"
    assert body["review_summary"] == {"approved_theme_count": 1, "rejected_theme_count": 1, "unreviewed_theme_count": 1}
    assert len(body["approved_themes"]) == 1

    approved_theme = body["approved_themes"][0]
    assert approved_theme["theme_id"] == approved.id
    assert approved_theme["name"] == "Battery Drain After Update"
    assert approved_theme["problem_statement"] == "Users report battery drain after the latest update."
    assert approved_theme["historical_match_id"] == note.id
    assert approved_theme["historical_commentary"] == "Matches a known historical battery issue."
    assert approved_theme["historical_similarity_score"] == 0.66
    assert approved_theme["advisory_confidence"] == 0.91
    assert approved_theme["analytics"] == {
        "feedback_count": 2,
        "source_distribution": {"email": 1, "web": 1},
        "user_type_distribution": {"admin": 1, "member": 1},
        "frequency_over_time": [{"week_start": "2026-07-20", "count": 1}, {"week_start": "2026-07-27", "count": 1}],
        "recurrence": "recurring",
    }
    supporting_ids = [item["feedback_item_id"] for item in approved_theme["supporting_feedback"]]
    assert supporting_ids == [items[0].id, items[1].id]

    report_id = body["report_id"]
    detail = client[0].get(f"/api/v1/reports/{report_id}")
    assert detail.status_code == 200
    assert detail.json() == body

    session = client[1]()
    audit = session.scalars(select(AuditLog).where(AuditLog.action == "report_created")).one()
    assert audit.ingest_id == ingest.id
    assert audit.details["report_id"] == report_id
    assert audit.details["approved_theme_count"] == 1
    session.close()


def test_ai_problem_statement_persists_into_theme_detail_and_report_snapshot(client, monkeypatch):
    data = ingest(client[0])
    ids = [row["id"] for row in data["preview"]]
    note = client[0].post("/api/v1/historical-notes", json={"product_area": "search", "title": "Battery note", "note": "Historically similar battery issue."}).json()
    problem_statement = "Users report battery drain after the latest update."
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: _ai_json_response(ids, problem_statement, note["id"]))

    analysis = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis").json()
    assert analysis["status"] == "completed"

    session = client[1]()
    theme = session.query(Theme).one()
    assert theme.problem_statement == problem_statement
    session.close()

    theme_detail = client[0].get(f"/api/v1/themes/{theme.id}")
    assert theme_detail.status_code == 200
    assert theme_detail.json()["problem_statement"] == problem_statement

    client[0].post(f"/api/v1/themes/{theme.id}/approve")
    report = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/reports")
    assert report.status_code == 201
    report_body = report.json()
    assert report_body["approved_themes"][0]["problem_statement"] == problem_statement

    persisted = client[0].get(f"/api/v1/reports/{report_body['report_id']}")
    assert persisted.status_code == 200
    assert persisted.json()["approved_themes"][0]["problem_statement"] == problem_statement


def test_report_snapshot_is_immutable_and_list_orders_newest_first(client):
    session = client[1]()
    ingest, approved, rejected, suggested, items, note = _seed_reviewed_ingest(session)
    session.close()

    first = client[0].post(f"/api/v1/ingests/{ingest.id}/reports").json()

    client[0].patch(f"/api/v1/themes/{approved.id}/rename", json={"name": "Battery Drain on Startup"})
    session = client[1]()
    theme = session.get(Theme, approved.id)
    theme.problem_statement = "Users report battery drain on startup after the latest update."
    session.commit()
    session.close()

    second = client[0].post(f"/api/v1/ingests/{ingest.id}/reports").json()

    list_response = client[0].get(f"/api/v1/ingests/{ingest.id}/reports")
    assert list_response.status_code == 200
    assert [item["report_id"] for item in list_response.json()] == [second["report_id"], first["report_id"]]

    first_detail = client[0].get(f"/api/v1/reports/{first['report_id']}").json()
    second_detail = client[0].get(f"/api/v1/reports/{second['report_id']}").json()
    assert first_detail["approved_themes"][0]["name"] == "Battery Drain After Update"
    assert first_detail["approved_themes"][0]["problem_statement"] == "Users report battery drain after the latest update."
    assert second_detail["approved_themes"][0]["name"] == "Battery Drain on Startup"
    assert second_detail["approved_themes"][0]["problem_statement"] == "Users report battery drain on startup after the latest update."

    session = client[1]()
    assert session.scalars(select(Report).where(Report.ingest_id == ingest.id)).all().__len__() == 2
    session.close()


def test_report_creation_validation_and_404s(client):
    missing_ingest = client[0].post("/api/v1/ingests/not-a-real-ingest/reports")
    assert missing_ingest.status_code == 404
    assert missing_ingest.json()["detail"] == {"code": "ingest_not_found"}

    session = client[1]()
    ingest = Ingest(id=str(uuid4()), filename="no-approved.csv", total_rows=1, valid_rows=1)
    session.add(ingest)
    item = FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=2, feedback_text="Unreviewed only", source="web", user_type="guest", product_area="search", feedback_date=date(2026, 8, 1), rating=None, original_values={"Feedback Text": "Unreviewed only"})
    theme = Theme(id=str(uuid4()), ingest_id=ingest.id, name="Unreviewed", description="desc", problem_statement="ps", review_status="suggested", ai_suggested=True)
    session.add_all([item, theme, ThemeMembership(id=str(uuid4()), theme_id=theme.id, feedback_item_id=item.id)])
    session.commit()
    session.close()

    no_approved = client[0].post(f"/api/v1/ingests/{ingest.id}/reports")
    assert no_approved.status_code == 409
    assert no_approved.json()["detail"]["code"] == "no_approved_themes"

    missing_report = client[0].get("/api/v1/reports/not-a-real-report")
    assert missing_report.status_code == 404
    assert missing_report.json()["detail"] == {"code": "report_not_found"}