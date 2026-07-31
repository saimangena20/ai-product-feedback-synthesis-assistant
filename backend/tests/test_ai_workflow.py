from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.historical_theme import HistoricalProductNote
from app.services.ai_service import AnalysisFailure


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


CSV = "Feedback Text,Source,User Type,Product Area,Date\ncrashes often,email,admin,search,2026-07-28\ncrashes again,web,member,search,2026-07-29\n"


def ingest(client):
    return client.post("/api/v1/ingests", files={"file": ("evidence.csv", BytesIO(CSV.encode()), "text/csv")}).json()


def valid_response(item_ids, note_id=None):
    theme = {"suggested_theme_label": "Search crashes", "suggested_problem_statement": "Users report crashes while searching.", "cited_feedback_ids": item_ids, "advisory_confidence": 0.7}
    if note_id:
        theme.update({"historical_match_id": note_id, "historical_commentary": "Possible similarity to a prior note.", "similarity_score": 0.6})
    return '{"themes": [' + __import__("json").dumps(theme) + ']}'


def test_valid_evidence_creates_unapproved_ai_suggested_theme(client, monkeypatch):
    data = ingest(client[0])
    ids = [row["id"] for row in data["preview"]]
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids))
    job = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis").json()
    assert job["status"] == "completed"
    session = client[1]()
    from app.models.theme import Theme
    theme = session.query(Theme).one()
    detail = client[0].get(f"/api/v1/themes/{theme.id}").json()
    assert detail["ai_suggested"] is True and detail["review_status"] == "suggested"
    assert detail["analytics"]["member_count"] == 2


@pytest.mark.parametrize("response,code", [
    ('{"themes":[{"suggested_theme_label":"x","suggested_problem_statement":"y","cited_feedback_ids":[]}]}', "malformed_provider_json"),
    ('not json', "malformed_provider_json"),
])
def test_missing_citations_or_malformed_json_fail_job(client, monkeypatch, response, code):
    data = ingest(client[0])
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: response)
    job = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis").json()
    assert job["status"] == "failed" and job["error_code"] == code


def test_invalid_citation_and_provider_failure_can_retry(client, monkeypatch):
    data = ingest(client[0])
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(["not-in-ingest"]))
    failed = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis").json()
    assert failed["error_code"] == "invalid_citations"
    ids = [item["id"] for item in data["preview"]]
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids))
    retried = client[0].post(f"/api/v1/analysis-jobs/{failed['job_id']}/retry").json()
    assert retried["status"] == "completed" and retried["attempt_count"] == 2


def test_provider_failure_is_persisted(client, monkeypatch):
    data = ingest(client[0])
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: (_ for _ in ()).throw(AnalysisFailure("provider_failure", "provider unavailable")))
    job = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis").json()
    assert job["status"] == "failed" and job["error_code"] == "provider_failure"


def test_historical_match_is_advisory_with_explicit_score(client, monkeypatch):
    data = ingest(client[0])
    note = client[0].post("/api/v1/historical-notes", json={"product_area": "search", "title": "Earlier crashes", "note": "A prior investigation."}).json()
    ids = [item["id"] for item in data["preview"]]
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids, note["id"]))
    client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis")
    session = client[1]()
    from app.models.theme import Theme
    theme = session.query(Theme).one()
    match = client[0].get(f"/api/v1/themes/{theme.id}").json()["historical_match"]
    assert match == {"note_id": note["id"], "commentary": "Possible similarity to a prior note.", "similarity_score": 0.6, "advisory": True}


def test_merge_and_split_keep_membership_analytics_correct(client, monkeypatch):
    data = ingest(client[0])
    ids = [item["id"] for item in data["preview"]]
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids))
    client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis")
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response([ids[0]]).replace("Search crashes", "Second theme"))
    client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis")
    session = client[1]()
    from app.models.theme import Theme
    themes = session.query(Theme).order_by(Theme.name).all()
    target = next(theme for theme in themes if theme.name == "Search crashes")
    source = next(theme for theme in themes if theme.name == "Second theme")
    merged = client[0].post(f"/api/v1/themes/{target.id}/merge", json={"source_theme_ids": [source.id]})
    assert merged.status_code == 200
    assert client[0].get(f"/api/v1/themes/{target.id}").json()["analytics"]["member_count"] == 2
    split = client[0].post(f"/api/v1/themes/{target.id}/split", json={"name": "Split off", "feedback_item_ids": [ids[0]]})
    assert split.status_code == 201
    assert client[0].get(f"/api/v1/themes/{target.id}").json()["analytics"]["member_count"] == 1
    assert client[0].get(f"/api/v1/themes/{split.json()['theme_id']}").json()["analytics"]["member_count"] == 1
