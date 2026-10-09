from app.corrections import router as corrections_router
from app.bulk_evidence import router as bulk_router
import hashlib
import json

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Job
from app.schemas import JobCreate, JobRead
from app.evidence import router as evidence_router

app = FastAPI(title="AI Career Application Agent", version="0.2.0")
app.include_router(evidence_router)


@app.get("/health")
def health():
    """Process liveness only; readiness separately checks the database/schema."""
    return {"status": "ok", "phase": 2, "submission_enabled": False}


@app.get("/ready")
def ready(session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1 FROM jobs LIMIT 1"))
        session.execute(text("SELECT 1 FROM source_documents LIMIT 1"))
        session.execute(text("SELECT 1 FROM career_facts LIMIT 1"))
        session.execute(text("SELECT 1 FROM fact_reviews LIMIT 1"))
        session.execute(text("SELECT 1 FROM fact_corrections LIMIT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable or migrations not applied")
    return {"status": "ready"}


@app.post("/jobs", response_model=JobRead, status_code=201)
def create_job(payload: JobCreate, session: Session = Depends(get_session)):
    # Conservative deduplication: same employer/title and exact description
    # after case/whitespace normalization. Not fuzzy matching across job IDs.
    parts = [" ".join(value.casefold().split()) for value in
             (payload.company, payload.title, payload.description)]
    fingerprint = hashlib.sha256(json.dumps(parts).encode()).hexdigest()
    record = Job(**payload.model_dump(exclude={"source_url"}),
                 source_url=str(payload.source_url) if payload.source_url else None,
                 content_hash=fingerprint)
    session.add(record)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "This job description is already saved")
    session.refresh(record)
    return record


@app.get("/jobs", response_model=list[JobRead])
def list_jobs(limit: int = 50, offset: int = 0, session: Session = Depends(get_session)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "limit must be 1–100 and offset must be nonnegative")
    return session.scalars(select(Job).order_by(Job.created_at.desc(), Job.id)
                           .limit(limit).offset(offset)).all()


@app.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, session: Session = Depends(get_session)):
    record = session.get(Job, job_id)
    if record is None:
        raise HTTPException(404, "Job not found")
    return record

app.include_router(bulk_router)

app.include_router(corrections_router)
