"""Corrections create linked pending replacements and preserve prior evidence/history."""
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.evidence import apply_review, check_source
from app.evidence_schemas import FactCreate, ReviewCreate
from app.models import CareerFact, FactCorrection
from app.bulk_evidence import normalized

router = APIRouter(tags=["Fact corrections"])


class CorrectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    statement: str = Field(min_length=5, max_length=5000)
    category: FactCreate.__annotations__["category"]
    expected_revision: int = Field(ge=0)
    reason: str = Field(min_length=5, max_length=4000)


class CorrectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    original_fact_id: str
    replacement_fact_id: str
    reason: str
    actor: str
    created_at: datetime


@router.get("/fact-corrections", response_model=list[CorrectionRead])
def list_corrections(limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0), session: Session = Depends(get_session)):
    return session.scalars(select(FactCorrection).order_by(FactCorrection.created_at, FactCorrection.id).limit(limit).offset(offset)).all()


@router.post("/facts/{fact_id}/corrections", response_model=CorrectionRead, status_code=201)
def correct_fact(fact_id: str, payload: CorrectionCreate, session: Session = Depends(get_session)):
    original = session.get(CareerFact, fact_id)
    if original is None:
        raise HTTPException(404, "Fact not found")
    if session.scalar(select(FactCorrection).where(FactCorrection.original_fact_id == fact_id)):
        raise HTTPException(409, "This fact already has a replacement; correct the latest replacement instead")
    if original.revision != payload.expected_revision:
        raise HTTPException(409, "Fact changed; refresh before correcting")
    if payload.statement == original.statement and payload.category == original.category:
        raise HTTPException(422, "Change the statement or category; use a review note for clarification only")
    if original.source_document_id:
        check_source(original.source_document_id, session)
    key = normalized(payload.statement)
    other_facts = session.scalars(select(CareerFact).where(CareerFact.id != fact_id, CareerFact.status != "rejected")).all()
    if any(normalized(fact.statement) == key and fact.category == payload.category for fact in other_facts):
        raise HTTPException(409, "An active fact already has that statement and category; review the existing entry")
    replacement_id = str(uuid4())
    replacement = CareerFact(id=replacement_id, statement=payload.statement, category=payload.category,
        provenance_kind=original.provenance_kind, source_document_id=original.source_document_id,
        source_locator=original.source_locator, evidence_note=original.evidence_note, status="pending", revision=0)
    correction = FactCorrection(original_fact_id=fact_id, replacement_fact_id=replacement_id, reason=payload.reason)
    try:
        apply_review(fact_id, ReviewCreate(decision="rejected", expected_revision=payload.expected_revision,
            note=f"Superseded by corrected fact {replacement_id}. Reason: {payload.reason}"), session)
        session.add(replacement)
        session.flush()
        session.add(correction)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Another correction was saved; refresh before continuing")
    except Exception:
        session.rollback()
        raise
    session.refresh(correction)
    return correction
