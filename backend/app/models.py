from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_jobs_content_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("sha256", name="uq_source_documents_sha256"),
        CheckConstraint("document_kind IN ('htcmf','master_resume','supporting')", name="ck_source_kind"),
        CheckConstraint("size_bytes > 0", name="ck_source_size"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    original_filename: Mapped[str] = mapped_column(String(255))
    document_kind: Mapped[str] = mapped_column(String(30))
    version_label: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_filename: Mapped[str] = mapped_column(String(50))
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CareerFact(Base):
    __tablename__ = "career_facts"
    __table_args__ = (
        CheckConstraint("status IN ('pending','verified','rejected')", name="ck_fact_status"),
        CheckConstraint("provenance_kind IN ('document','user_confirmation')", name="ck_fact_provenance"),
        CheckConstraint("(provenance_kind = 'document' AND source_document_id IS NOT NULL) OR (provenance_kind = 'user_confirmation' AND source_document_id IS NULL)", name="ck_fact_source"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    statement: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50))
    provenance_kind: Mapped[str] = mapped_column(String(30))
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=True)
    source_locator: Mapped[str] = mapped_column(String(500))
    evidence_note: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class FactReview(Base):
    __tablename__ = "fact_reviews"
    __table_args__ = (
        UniqueConstraint("fact_id", "revision", name="uq_fact_review_revision"),
        CheckConstraint("decision IN ('pending','verified','rejected')", name="ck_review_decision"),
        CheckConstraint("decision != 'verified' OR verification_basis IS NOT NULL", name="ck_review_basis"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    fact_id: Mapped[str] = mapped_column(ForeignKey("career_facts.id", ondelete="RESTRICT"))
    revision: Mapped[int] = mapped_column(Integer)
    previous_status: Mapped[str] = mapped_column(String(20))
    decision: Mapped[str] = mapped_column(String(20))
    verification_basis: Mapped[str | None] = mapped_column(String(40), nullable=True)
    note: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(50), default="local_user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class FactCorrection(Base):
    __tablename__ = "fact_corrections"
    __table_args__ = (
        UniqueConstraint("original_fact_id", name="uq_correction_original"),
        UniqueConstraint("replacement_fact_id", name="uq_correction_replacement"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    original_fact_id: Mapped[str] = mapped_column(ForeignKey("career_facts.id", ondelete="RESTRICT"))
    replacement_fact_id: Mapped[str] = mapped_column(ForeignKey("career_facts.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(50), default="local_user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
