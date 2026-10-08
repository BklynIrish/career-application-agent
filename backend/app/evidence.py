import hashlib
import io
import os
from pathlib import Path
from uuid import uuid4
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.evidence_schemas import DocumentKind, FactCreate, FactRead, FactStatus, ReviewCreate, ReviewRead, SourceRead
from app.models import CareerFact, FactReview, SourceDocument

router = APIRouter(tags=["Evidence"])
MAX_SOURCE_BYTES = 10 * 1024 * 1024


def source_root():
    # Independent of the terminal's working directory; override only for tests.
    return Path(os.environ.get("SOURCE_STORAGE_DIR", str(Path(__file__).resolve().parents[2] / "private" / "sources")))


def validate_bytes(filename, data):
    suffix = Path(filename).suffix.lower()
    if suffix not in {".docx", ".pdf", ".txt", ".md"}:
        raise HTTPException(415, "Use a DOCX, PDF, TXT, or MD document")
    if not data:
        raise HTTPException(422, "Empty documents cannot be registered")
    if suffix == ".pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(422, "File does not have a PDF header")
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(archive.namelist()):
                    raise ValueError()
                if sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
                    raise ValueError()
        except (zipfile.BadZipFile, ValueError):
            raise HTTPException(422, "File is not a supported DOCX document")
    if suffix in {".txt", ".md"}:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(422, "Text documents must use UTF-8 encoding")
    return suffix


@router.post("/sources", response_model=SourceRead, status_code=201)
def upload_source(
    file: UploadFile = File(...),
    document_kind: DocumentKind = Form(...),
    version_label: str = Form(..., min_length=1, max_length=100),
    supersedes_id: str | None = Form(None),
    session: Session = Depends(get_session),
):
    label = version_label.strip()
    if not label:
        raise HTTPException(422, "Enter a version label")
    if supersedes_id:
        parent = session.get(SourceDocument, supersedes_id)
        if not parent or parent.document_kind != document_kind:
            raise HTTPException(422, "Previous version must be an existing document of the same kind")
    filename = (file.filename or "document").replace("\\", "/").split("/")[-1]
    if len(filename) > 255 or any(ord(char) < 32 for char in filename):
        raise HTTPException(422, "Invalid filename")
    data = file.file.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise HTTPException(413, "Document limit is 10 MiB")
    suffix = validate_bytes(filename, data)
    digest = hashlib.sha256(data).hexdigest()
    if session.scalar(select(SourceDocument).where(SourceDocument.sha256 == digest)):
        raise HTTPException(409, "These exact document bytes are already registered")
    source_id = str(uuid4())
    stored_name = source_id + suffix
    root = source_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / stored_name
    record = SourceDocument(id=source_id, original_filename=filename, document_kind=document_kind,
                            version_label=label, sha256=digest, size_bytes=len(data),
                            storage_filename=stored_name, supersedes_id=supersedes_id)
    created_file = False
    try:
        # Exclusive creation; upload filename never controls the storage path.
        with path.open("xb") as output:
            created_file = True
            output.write(data)
        path.chmod(0o400)
        session.add(record)
        session.commit()
    except Exception as error:
        session.rollback()
        if created_file and path.exists():
            path.unlink()
        if isinstance(error, IntegrityError):
            raise HTTPException(409, "These exact document bytes are already registered")
        raise
    session.refresh(record)
    return record


@router.get("/sources", response_model=list[SourceRead])
def list_sources(limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0), session: Session = Depends(get_session)):
    return session.scalars(select(SourceDocument).order_by(SourceDocument.created_at.desc(), SourceDocument.id).limit(limit).offset(offset)).all()


@router.get("/sources/{source_id}/integrity")
def check_source(source_id: str, session: Session = Depends(get_session)):
    record = session.get(SourceDocument, source_id)
    if not record:
        raise HTTPException(404, "Source not found")
    path = source_root() / record.storage_filename
    if not path.is_file():
        raise HTTPException(409, "Registered source copy is missing")
    with path.open("rb") as stored:
        digest = hashlib.file_digest(stored, "sha256").hexdigest()
    if digest != record.sha256:
        raise HTTPException(409, "Registered source copy has changed")
    return {"status": "intact", "source_id": source_id}


@router.post("/facts", response_model=FactRead, status_code=201)
def create_fact(payload: FactCreate, session: Session = Depends(get_session)):
    if payload.source_document_id and not session.get(SourceDocument, payload.source_document_id):
        raise HTTPException(422, "Source document not found")
    fact = CareerFact(**payload.model_dump(), status="pending", revision=0)
    session.add(fact)
    session.commit()
    session.refresh(fact)
    return fact


@router.get("/facts", response_model=list[FactRead])
def list_facts(status: FactStatus | None = None, limit: int = Query(100, ge=1, le=100),
               offset: int = Query(0, ge=0), session: Session = Depends(get_session)):
    query = select(CareerFact)
    if status:
        query = query.where(CareerFact.status == status)
    return session.scalars(query.order_by(CareerFact.created_at.desc(), CareerFact.id).limit(limit).offset(offset)).all()


@router.post("/facts/{fact_id}/reviews", response_model=FactRead)
def review_fact(fact_id: str, payload: ReviewCreate, session: Session = Depends(get_session)):
    fact = session.get(CareerFact, fact_id)
    if not fact:
        raise HTTPException(404, "Fact not found")
    if fact.source_document_id and payload.decision == "verified":
        check_source(fact.source_document_id, session)
    previous = fact.status
    revision = payload.expected_revision + 1
    changed = session.execute(update(CareerFact).where(CareerFact.id == fact_id,
        CareerFact.revision == payload.expected_revision).values(status=payload.decision, revision=revision),
        execution_options={"synchronize_session": False})
    if changed.rowcount != 1:
        session.rollback()
        raise HTTPException(409, "Fact was reviewed elsewhere; refresh before reviewing again")
    session.add(FactReview(fact_id=fact_id, revision=revision, previous_status=previous,
                          decision=payload.decision, verification_basis=payload.verification_basis,
                          note=payload.note, actor="local_user"))
    session.commit()
    session.refresh(fact)
    return fact


@router.get("/facts/{fact_id}/reviews", response_model=list[ReviewRead])
def review_history(fact_id: str, session: Session = Depends(get_session)):
    if not session.get(CareerFact, fact_id):
        raise HTTPException(404, "Fact not found")
    return session.scalars(select(FactReview).where(FactReview.fact_id == fact_id).order_by(FactReview.revision)).all()
