from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DocumentKind = Literal["htcmf", "master_resume", "supporting"]
FactStatus = Literal["pending", "verified", "rejected"]
Basis = Literal["user_confirmed", "document_supported", "independently_documented"]


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    original_filename: str
    document_kind: str
    version_label: str
    sha256: str
    size_bytes: int
    supersedes_id: str | None
    created_at: datetime


class FactCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    statement: str = Field(min_length=5, max_length=5000)
    category: Literal["experience", "metric", "education", "skill", "project", "other"]
    provenance_kind: Literal["document", "user_confirmation"]
    source_document_id: str | None = None
    source_locator: str = Field(min_length=1, max_length=500)
    evidence_note: str = Field(min_length=5, max_length=5000)

    @model_validator(mode="after")
    def source_required(self):
        if self.provenance_kind == "document" and not self.source_document_id:
            raise ValueError("Choose a source document")
        if self.provenance_kind == "user_confirmation" and self.source_document_id:
            raise ValueError("User confirmation uses an attestation note, not a document link")
        return self


class FactRead(FactCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    revision: int
    created_at: datetime


class ReviewCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    decision: FactStatus
    expected_revision: int = Field(ge=0)
    verification_basis: Basis | None = None
    note: str = Field(min_length=5, max_length=5000)

    @model_validator(mode="after")
    def basis_required(self):
        if self.decision == "verified" and not self.verification_basis:
            raise ValueError("Verification requires a basis")
        if self.decision != "verified" and self.verification_basis:
            raise ValueError("Only verification has a verification basis")
        return self


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    fact_id: str
    revision: int
    previous_status: str
    decision: str
    verification_basis: str | None
    note: str
    actor: str
    created_at: datetime
