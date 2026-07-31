from io import BytesIO
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.feedback import FeedbackItem, Ingest
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


VALID_HEADERS = "Feedback Text,Source,User Type,Product Area,Date,Rating\n"


def upload(client, csv_text: str):
    return client.post("/api/v1/ingests", files={"file": ("feedback.csv", BytesIO(csv_text.encode()), "text/csv")})


def test_valid_upload_persists_snapshot_preview_and_rows(client):
    response = upload(client[0], VALID_HEADERS + "Great search,web,admin,search,2026-07-30,4.5\n")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == body["job_status"] == "completed"
    assert body["preview"][0]["row_number"] == 2
    assert body["preview"][0]["rating"] == 4.5
    detail = client[0].get(f"/api/v1/ingests/{body['ingest_id']}")
    assert detail.json()["feedback_items"][0]["original_values"]["Feedback Text"] == "Great search"


def test_missing_headers_are_actionable(client):
    response = upload(client[0], "Feedback Text,Source\nhello,web\n")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "missing_headers"
    assert {entry["column"] for entry in response.json()["detail"]["errors"]} == {"user type", "product area", "date"}


def test_malformed_date_is_row_numbered(client):
    response = upload(client[0], VALID_HEADERS + "Broken,web,admin,search,30-07-2026,\n")
    assert response.status_code == 422
    error = response.json()["detail"]["errors"][0]
    assert error["row"] == 2 and error["column"] == "date"


def test_optional_rating_can_be_blank(client):
    response = upload(client[0], VALID_HEADERS + "No rating,web,admin,search,2026-07-30,\n")
    assert response.status_code == 201
    assert response.json()["preview"][0]["rating"] is None


def test_identical_rows_remain_distinct(client):
    line = "Same evidence,web,admin,search,2026-07-30,5\n"
    response = upload(client[0], VALID_HEADERS + line + line)
    assert response.status_code == 201
    assert response.json()["valid_rows"] == 2
    assert len(client[0].get(f"/api/v1/ingests/{response.json()['ingest_id']}").json()["feedback_items"]) == 2


def test_theme_analytics_use_memberships_only_and_are_deterministic(client):
    session: Session = client[1]()
    ingest = Ingest(id=str(uuid4()), filename="seed.csv", total_rows=3, valid_rows=3)
    session.add(ingest)
    items = [
        FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=2, feedback_text="a", source="email", user_type="admin", product_area="x", feedback_date=date(2026, 7, 27), rating=None, original_values={}),
        FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=3, feedback_text="b", source="web", user_type="member", product_area="x", feedback_date=date(2026, 8, 2), rating=None, original_values={}),
        FeedbackItem(id=str(uuid4()), ingest_id=ingest.id, row_number=4, feedback_text="not a member", source="web", user_type="member", product_area="x", feedback_date=date(2026, 8, 3), rating=None, original_values={}),
    ]
    session.add_all(items)
    theme = Theme(id=str(uuid4()), ingest_id=ingest.id, name="Onboarding")
    session.add(theme)
    session.add_all([ThemeMembership(id=str(uuid4()), theme_id=theme.id, feedback_item_id=items[0].id), ThemeMembership(id=str(uuid4()), theme_id=theme.id, feedback_item_id=items[1].id)])
    session.commit()
    session.close()
    response = client[0].get(f"/api/v1/themes/{theme.id}")
    analytics = response.json()["analytics"]
    assert analytics == {"member_count": 2, "distribution_by_source": {"email": 1, "web": 1}, "distribution_by_user_type": {"admin": 1, "member": 1}, "frequency_over_time": [{"week_start": "2026-07-27", "count": 2}], "recurrence": "recurring"}
    assert len(response.json()["feedback_items"]) == 2
