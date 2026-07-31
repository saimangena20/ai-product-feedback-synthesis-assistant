"""create core feedback ingest and theme schema"""
from alembic import op
import sqlalchemy as sa

revision = "20260731_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("ingests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("filename", sa.String(255), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("job_status", sa.String(32), nullable=False), sa.Column("total_rows", sa.Integer(), nullable=False), sa.Column("valid_rows", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("csv_snapshots", sa.Column("id", sa.String(36), primary_key=True), sa.Column("ingest_id", sa.String(36), sa.ForeignKey("ingests.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("content", sa.LargeBinary(), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("feedback_items", sa.Column("id", sa.String(36), primary_key=True), sa.Column("ingest_id", sa.String(36), sa.ForeignKey("ingests.id", ondelete="CASCADE"), nullable=False), sa.Column("row_number", sa.Integer(), nullable=False), sa.Column("feedback_text", sa.Text(), nullable=False), sa.Column("source", sa.String(255), nullable=False), sa.Column("user_type", sa.String(255), nullable=False), sa.Column("product_area", sa.String(255), nullable=False), sa.Column("feedback_date", sa.Date(), nullable=False), sa.Column("rating", sa.Numeric(12, 4)), sa.Column("original_values", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("ingest_id", "row_number", name="uq_feedback_items_ingest_row"))
    op.create_index("ix_feedback_items_ingest_id", "feedback_items", ["ingest_id"])
    op.create_table("themes", sa.Column("id", sa.String(36), primary_key=True), sa.Column("ingest_id", sa.String(36), sa.ForeignKey("ingests.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("ingest_id", "name", name="uq_themes_ingest_name"))
    op.create_index("ix_themes_ingest_id", "themes", ["ingest_id"])
    op.create_table("theme_memberships", sa.Column("id", sa.String(36), primary_key=True), sa.Column("theme_id", sa.String(36), sa.ForeignKey("themes.id", ondelete="CASCADE"), nullable=False), sa.Column("feedback_item_id", sa.String(36), sa.ForeignKey("feedback_items.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("theme_id", "feedback_item_id", name="uq_theme_membership"))
    op.create_index("ix_theme_memberships_theme_id", "theme_memberships", ["theme_id"])
    op.create_index("ix_theme_memberships_feedback_item_id", "theme_memberships", ["feedback_item_id"])
    op.create_table("audit_logs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("ingest_id", sa.String(36), sa.ForeignKey("ingests.id", ondelete="SET NULL")), sa.Column("action", sa.String(100), nullable=False), sa.Column("outcome", sa.String(32), nullable=False), sa.Column("details", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_logs_ingest_id", "audit_logs", ["ingest_id"])
    op.create_table("historical_themes", sa.Column("id", sa.String(36), primary_key=True), sa.Column("theme_name", sa.String(255), nullable=False), sa.Column("occurrence_count", sa.Integer(), nullable=False), sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False), sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False))
    op.create_table("reports", sa.Column("id", sa.String(36), primary_key=True), sa.Column("ingest_id", sa.String(36), sa.ForeignKey("ingests.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("payload", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_reports_ingest_id", "reports", ["ingest_id"])


def downgrade() -> None:
    for table in ("reports", "historical_themes", "audit_logs", "theme_memberships", "themes", "feedback_items", "csv_snapshots", "ingests"):
        op.drop_table(table)
