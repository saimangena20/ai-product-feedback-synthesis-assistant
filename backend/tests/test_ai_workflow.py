from io import BytesIO
from datetime import date
from uuid import uuid4

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


def test_generate_ai_json_requests_structured_json(monkeypatch):
    from app.services import ai_service

    calls = {}

    class FakeResponse:
        text = '{"themes": []}'

    class FakeModel:
        def __init__(self, model_name):
            calls["model_name"] = model_name

        def generate_content(self, prompt, generation_config=None):
            calls["prompt"] = prompt
            calls["generation_config"] = generation_config
            return FakeResponse()

    monkeypatch.setattr(ai_service.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr("google.generativeai.configure", lambda api_key: calls.setdefault("api_key", api_key))
    monkeypatch.setattr("google.generativeai.GenerativeModel", FakeModel)

    result = ai_service.generate_ai_json("test prompt")

    assert result == '{"themes": []}'
    assert calls["api_key"] == "test-key"
    assert calls["model_name"] == ai_service.settings.gemini_model
    assert calls["generation_config"].response_mime_type == "application/json"
    assert calls["generation_config"].response_schema is ai_service.SuggestionEnvelopePayload
    assert calls["generation_config"].temperature == 0.0


def test_valid_evidence_creates_unapproved_ai_suggested_theme(client, monkeypatch):
    data = ingest(client[0])
    ids = [row["id"] for row in data["preview"]]
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids))
    job = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis").json()
    assert job["status"] == "completed"
    session = client[1]()
    from app.models.theme import Theme
    theme = session.query(Theme).one()
    assert theme.problem_statement == "Users report crashes while searching."
    detail = client[0].get(f"/api/v1/themes/{theme.id}").json()
    assert detail["ai_suggested"] is True and detail["review_status"] == "suggested"
    assert detail["problem_statement"] == "Users report crashes while searching."
    assert detail["analytics"]["member_count"] == 2


def test_theme_detail_returns_null_problem_statement_when_not_persisted(client):
    from app.models.feedback import FeedbackItem, Ingest
    from app.models.theme import Theme, ThemeMembership

    session = client[1]()
    ingest = Ingest(id=str(uuid4()), filename="legacy.csv", total_rows=1, valid_rows=1)
    item = FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=2, feedback_text="Legacy theme", source="web", user_type="member", product_area="search", feedback_date=date(2026, 7, 28), rating=None, original_values={"Feedback Text": "Legacy theme"})
    theme = Theme(id=str(uuid4()), ingest_id=ingest.id, name="Legacy Theme", description="Human summary text", problem_statement=None, review_status="suggested")
    session.add_all([ingest, item, theme, ThemeMembership(id=str(uuid4()), theme_id=theme.id, feedback_item_id=item.id)])
    session.commit()
    session.close()

    detail = client[0].get(f"/api/v1/themes/{theme.id}").json()
    assert detail["description"] == "Human summary text"
    assert detail["problem_statement"] is None


def test_ingest_themes_returns_summary_and_deterministic_analytics(client, monkeypatch):
    data = ingest(client[0])
    ids = [row["id"] for row in data["preview"]]
    note = client[0].post("/api/v1/historical-notes", json={"product_area": "search", "title": "Earlier crashes", "note": "A prior investigation."}).json()
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids, note["id"]))
    client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis")

    response = client[0].get(f"/api/v1/ingests/{data['ingest_id']}/themes")

    assert response.status_code == 200
    body = response.json()
    assert body["ingest_id"] == data["ingest_id"]
    assert len(body["themes"]) == 1
    theme = body["themes"][0]
    assert theme["id"]
    assert theme["ingest_id"] == data["ingest_id"]
    assert theme["ai_suggested"] is True
    assert theme["problem_statement"] == "Users report crashes while searching."
    assert theme["historical_match_id"] == note["id"]
    assert theme["historical_commentary"] == "Possible similarity to a prior note."
    assert theme["historical_similarity_score"] == 0.6
    assert theme["analytics"] == {
        "feedback_count": 2,
        "source_distribution": {"email": 1, "web": 1},
        "user_type_distribution": {"admin": 1, "member": 1},
        "frequency_over_time": [{"week_start": "2026-07-27", "count": 2}],
    }


def test_ingest_themes_returns_empty_array_when_no_themes_exist(client):
    data = ingest(client[0])

    response = client[0].get(f"/api/v1/ingests/{data['ingest_id']}/themes")

    assert response.status_code == 200
    assert response.json() == {"ingest_id": data["ingest_id"], "themes": []}


def test_ingest_themes_returns_404_for_missing_ingest(client):
    response = client[0].get("/api/v1/ingests/not-a-real-ingest/themes")

    assert response.status_code == 404
    assert response.json()["detail"] == {"code": "ingest_not_found"}


def test_retrying_failed_analysis_does_not_duplicate_themes_and_preserves_reviewed_data(client, monkeypatch):
    data = ingest(client[0])
    ids = [row["id"] for row in data["preview"]]

    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids))
    first_job = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis").json()
    assert first_job["status"] == "completed"

    session = client[1]()
    from app.models.theme import Theme
    theme = session.query(Theme).one()
    client[0].post(f"/api/v1/themes/{theme.id}/approve")
    reviewed_name = theme.name
    session.close()

    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: (_ for _ in ()).throw(AnalysisFailure("provider_failure", "provider unavailable")))
    failed_job = client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis").json()
    assert failed_job["status"] == "failed"

    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids).replace("Search crashes", "Battery Drain After Update"))
    retried_job = client[0].post(f"/api/v1/analysis-jobs/{failed_job['job_id']}/retry").json()
    assert retried_job["status"] == "completed"

    session = client[1]()
    themes = session.query(Theme).all()
    assert len(themes) == 1
    preserved = themes[0]
    assert preserved.review_status == "approved"
    assert preserved.name == reviewed_name
    assert preserved.problem_statement == "Users report crashes while searching."
    session.close()

    detail = client[0].get(f"/api/v1/themes/{preserved.id}").json()
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


def test_split_can_store_human_problem_statement(client, monkeypatch):
    data = ingest(client[0])
    ids = [item["id"] for item in data["preview"]]
    monkeypatch.setattr("app.services.ai_service.generate_ai_json", lambda prompt: valid_response(ids))
    client[0].post(f"/api/v1/ingests/{data['ingest_id']}/analysis")

    session = client[1]()
    from app.models.theme import Theme
    theme = session.query(Theme).one()
    session.close()

    response = client[0].post(
        f"/api/v1/themes/{theme.id}/split",
        json={"name": "Battery Drain - Split", "feedback_item_ids": [ids[0]], "problem_statement": "Battery drain worsens after the update."},
    )
    assert response.status_code == 201

    split_detail = client[0].get(f"/api/v1/themes/{response.json()['theme_id']}").json()
    assert split_detail["problem_statement"] == "Battery drain worsens after the update."
