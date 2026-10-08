"""Private source registry and reviewed career facts."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("source_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("document_kind", sa.String(30), nullable=False),
        sa.Column("version_label", sa.String(100), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_filename", sa.String(50), nullable=False),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("source_documents.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("sha256", name="uq_source_documents_sha256"),
        sa.CheckConstraint("document_kind IN ('htcmf','master_resume','supporting')", name="ck_source_kind"),
        sa.CheckConstraint("size_bytes > 0", name="ck_source_size"))
    op.create_table("career_facts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("statement", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("provenance_kind", sa.String(30), nullable=False),
        sa.Column("source_document_id", sa.String(36), sa.ForeignKey("source_documents.id", ondelete="RESTRICT")),
        sa.Column("source_locator", sa.String(500), nullable=False),
        sa.Column("evidence_note", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending','verified','rejected')", name="ck_fact_status"),
        sa.CheckConstraint("provenance_kind IN ('document','user_confirmation')", name="ck_fact_provenance"),
        sa.CheckConstraint("(provenance_kind = 'document' AND source_document_id IS NOT NULL) OR (provenance_kind = 'user_confirmation' AND source_document_id IS NULL)", name="ck_fact_source"))
    op.create_table("fact_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("fact_id", sa.String(36), sa.ForeignKey("career_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("verification_basis", sa.String(40)),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("actor", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("fact_id", "revision", name="uq_fact_review_revision"),
        sa.CheckConstraint("decision IN ('pending','verified','rejected')", name="ck_review_decision"),
        sa.CheckConstraint("decision != 'verified' OR verification_basis IS NOT NULL", name="ck_review_basis"))


def downgrade():
    op.drop_table("fact_reviews")
    op.drop_table("career_facts")
    op.drop_table("source_documents")
