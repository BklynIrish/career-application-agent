from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import Job, CareerFact, FactReview


def test_upgrade_preserves_phase1_jobs(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'migration.db'}")
    get_engine.cache_clear()
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    try:
        command.upgrade(config, "0001")
        engine = get_engine()
        with Session(engine) as session:
            session.add(Job(id="demo-job", title="Demo", company="Demo Healthcare", description="Synthetic saved job", source_kind="pasted", content_hash="a" * 64))
            session.commit()
        command.upgrade(config, "0002")
        with Session(engine) as session:
            session.add(CareerFact(id="existing-fact", statement="Existing synthetic claim", category="experience",
                provenance_kind="user_confirmation", source_locator="Test", evidence_note="Synthetic confirmation",
                status="verified", revision=1))
            session.flush()
            session.add(FactReview(fact_id="existing-fact", revision=1, previous_status="pending",
                decision="verified", verification_basis="user_confirmed", note="Existing review", actor="local_user"))
            session.commit()
        command.upgrade(config, "head")
        assert {"jobs", "source_documents", "career_facts", "fact_reviews", "fact_corrections"}.issubset(inspect(engine).get_table_names())
        with Session(engine) as session:
            assert session.scalar(select(Job)).id == "demo-job"
            assert session.get(CareerFact, "existing-fact").status == "verified"
            assert session.scalar(select(FactReview)).note == "Existing review"
    finally:
        get_engine().dispose()
        get_engine.cache_clear()
