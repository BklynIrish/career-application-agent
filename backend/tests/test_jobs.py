import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import app
from app.models import Base


@pytest.fixture
def client():
    # SQLite verifies portable API behavior; PostgreSQL is checked separately on Mac.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def override_session():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


JOB = {"title": "Implementation Specialist", "company": "Demo Healthcare",
       "description": "Remote healthcare implementation role requiring SQL and workflow analysis."}


def test_intake_list_and_detail(client):
    created = client.post("/jobs", json=JOB)
    assert created.status_code == 201
    record = created.json()
    assert client.get("/jobs").json()[0]["id"] == record["id"]
    assert client.get(f"/jobs/{record['id']}").json()["description"] == JOB["description"]
    assert client.get("/ready").status_code == 200


def test_duplicate_normalization(client):
    assert client.post("/jobs", json=JOB).status_code == 201
    changed = dict(JOB, title="  IMPLEMENTATION   SPECIALIST  ")
    assert client.post("/jobs", json=changed).status_code == 409
    assert len(client.get("/jobs").json()) == 1


def test_invalid_input(client):
    assert client.post("/jobs", json=dict(JOB, title="  ")).status_code == 422
    assert client.post("/jobs", json=dict(JOB, source_url="javascript:alert(1)")).status_code == 422
    assert client.post("/jobs", json=dict(JOB, description="short")).status_code == 422


def test_no_submission_route(client):
    assert client.get("/health").json()["submission_enabled"] is False
    assert client.post("/applications/submit", json={}).status_code == 404


def test_pagination_and_missing_record(client):
    assert client.get("/jobs?limit=101").status_code == 422
    assert client.get("/jobs?offset=-1").status_code == 422
    assert client.get("/jobs/missing").status_code == 404
