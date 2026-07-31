"""add evidence-first analysis jobs and theme review metadata"""
from alembic import op
import sqlalchemy as sa

revision = "20260731_0002"
down_revision = "20260731_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("historical_product_notes", sa.Column("id", sa.String(36), primary_key=True), sa.Column("product_area", sa.String(255), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("note", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_historical_product_notes_product_area", "historical_product_notes", ["product_area"])
    op.create_table("analysis_jobs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("ingest_id", sa.String(36), sa.ForeignKey("ingests.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("attempt_count", sa.Integer(), nullable=False), sa.Column("error_code", sa.String(100)), sa.Column("error_detail", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_analysis_jobs_ingest_id", "analysis_jobs", ["ingest_id"])
    with op.batch_alter_table("themes") as batch:
        batch.add_column(sa.Column("review_status", sa.String(32), nullable=False, server_default="suggested"))
        batch.add_column(sa.Column("ai_suggested", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("advisory_confidence", sa.Float()))
        batch.add_column(sa.Column("historical_match_id", sa.String(36), sa.ForeignKey("historical_product_notes.id", name="fk_themes_historical_match", ondelete="SET NULL")))
        batch.add_column(sa.Column("historical_commentary", sa.Text()))
        batch.add_column(sa.Column("historical_similarity_score", sa.Float()))
        batch.add_column(sa.Column("rejection_reason", sa.Text()))
        batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    with op.batch_alter_table("themes") as batch:
        for column in ("approved_at", "rejection_reason", "historical_similarity_score", "historical_commentary", "historical_match_id", "advisory_confidence", "ai_suggested", "review_status"):
            batch.drop_column(column)
    op.drop_table("analysis_jobs")
    op.drop_table("historical_product_notes")
