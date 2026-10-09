"""Local text extraction and explicit, transactional batch actions. No LLM calls."""
import hashlib
import re
import unicodedata
import zipfile
from difflib import SequenceMatcher
from xml.etree import ElementTree

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.evidence import check_source, source_root, apply_review
from app.evidence_schemas import FactCreate, ReviewCreate, FactStatus, Basis
from app.models import CareerFact, SourceDocument

router = APIRouter(tags=["Bulk evidence"])


def normalized(text):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


def extract(record):
    path = source_root() / record.storage_filename
    suffix = path.suffix.lower()
    try:
        if suffix == ".docx":
            with zipfile.ZipFile(path) as archive:
                if sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
                    raise HTTPException(422, "DOCX exceeds extraction limit")
                xml = archive.read("word/document.xml")
            if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                raise HTTPException(422, "Unsupported XML declarations")
            tree = ElementTree.fromstring(xml)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            rows = [(f"DOCX paragraph {i}", "".join(node.text or "" for node in p.findall(".//w:t", ns)).strip())
                    for i, p in enumerate(tree.findall(".//w:p", ns), 1)]
        elif suffix in {".txt", ".md"}:
            rows = [(f"Line {i}", line.strip()) for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)]
        else:
            raise HTTPException(415, "Bulk extraction supports DOCX, TXT and MD. PDF sources can still be registered and used manually.")
    except (OSError, KeyError, UnicodeError, zipfile.BadZipFile, ElementTree.ParseError):
        raise HTTPException(422, "Unable to extract document text")
    candidates = []
    for locator, text in rows:
        if len(text) < 5:
            continue
        # Keep entire source passages; never truncate a qualification or invent a claim.
        if len(text) > 5000:
            raise HTTPException(422, "A source passage exceeds 5,000 characters; use manual entry for this document")
        candidate_id = hashlib.sha256((locator + "\n" + text).encode()).hexdigest()
        candidates.append({"candidate_id": candidate_id, "statement": text, "source_locator": locator, "evidence_note": text})
    if len(candidates) > 200:
        raise HTTPException(422, "Document has more than 200 passages; use a smaller source or manual entry")
    return candidates


def checked_record(source_id, session):
    record = session.get(SourceDocument, source_id)
    if record is None:
        raise HTTPException(404, "Source not found")
    check_source(source_id, session)
    return record


@router.get("/sources/{source_id}/candidates")
def preview(source_id: str, session: Session = Depends(get_session)):
    record = checked_record(source_id, session)
    existing = session.scalars(select(CareerFact)).all()
    candidates = extract(record)
    for item in candidates:
        key = normalized(item["statement"])
        item["duplicate_fact_id"] = next((fact.id for fact in existing if normalized(fact.statement) == key), None)
        item["possible_matches"] = [{"id": fact.id, "statement": fact.statement, "status": fact.status}
            for fact in existing if normalized(fact.statement) != key
            and SequenceMatcher(None, key, normalized(fact.statement)).ratio() >= 0.6][:5]
    return {"source_id": source_id, "source_sha256": record.sha256, "candidates": candidates}


class ImportItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    candidate_id: str
    statement: str = Field(min_length=5, max_length=5000)
    category: FactCreate.__annotations__["category"] = "other"


class ImportBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_sha256: str
    items: list[ImportItem] = Field(min_length=1, max_length=200)


@router.post("/sources/{source_id}/facts/import")
def import_facts(source_id: str, payload: ImportBatch, session: Session = Depends(get_session)):
    record = checked_record(source_id, session)
    if payload.source_sha256 != record.sha256:
        raise HTTPException(409, "Source changed; preview again")
    passages = {item["candidate_id"]: item for item in extract(record)}
    prepared = []
    for item in payload.items:
        passage = passages.get(item.candidate_id)
        if passage is None:
            raise HTTPException(422, "Candidate is not part of this source")
        prepared.append(FactCreate(statement=item.statement, category=item.category, provenance_kind="document",
            source_document_id=source_id, source_locator=passage["source_locator"], evidence_note=passage["evidence_note"]))
    known = {normalized(fact.statement) for fact in session.scalars(select(CareerFact)).all()}
    created, skipped = [], 0
    for item in prepared:
        key = normalized(item.statement)
        if key in known:
            skipped += 1
            continue
        fact = CareerFact(**item.model_dump(), status="pending", revision=0)
        session.add(fact)
        created.append(fact)
        known.add(key)
    session.commit()
    return {"created": len(created), "skipped_duplicates": skipped, "status": "pending"}


class ReviewTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact_id: str
    expected_revision: int = Field(ge=0)


class ReviewBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: FactStatus
    verification_basis: Basis | None = None
    note: str = Field(min_length=5, max_length=5000)
    items: list[ReviewTarget] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_review(self):
        ReviewCreate(decision=self.decision, verification_basis=self.verification_basis,
                     note=self.note, expected_revision=0)
        return self


@router.post("/facts/bulk-reviews")
def bulk_reviews(payload: ReviewBatch, session: Session = Depends(get_session)):
    if len({item.fact_id for item in payload.items}) != len(payload.items):
        raise HTTPException(422, "Select each fact once")
    try:
        for item in payload.items:
            review = ReviewCreate(decision=payload.decision, expected_revision=item.expected_revision,
                verification_basis=payload.verification_basis, note=payload.note)
            apply_review(item.fact_id, review, session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"reviewed": len(payload.items), "decision": payload.decision}
