"""Link immutable facts to corrected replacements without altering source records."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("fact_corrections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_fact_id", sa.String(36), sa.ForeignKey("career_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("replacement_fact_id", sa.String(36), sa.ForeignKey("career_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("actor", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("original_fact_id", name="uq_correction_original"),
        sa.UniqueConstraint("replacement_fact_id", name="uq_correction_replacement"))


def downgrade():
    op.drop_table("fact_corrections")
