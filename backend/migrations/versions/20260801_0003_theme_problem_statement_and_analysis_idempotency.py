"""add theme problem statement"""
from alembic import op
import sqlalchemy as sa

revision = "20260801_0003"
down_revision = "20260731_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("themes") as batch:
        batch.add_column(sa.Column("problem_statement", sa.Text(), nullable=True))
    op.execute("UPDATE themes SET problem_statement = description WHERE problem_statement IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("themes") as batch:
        batch.drop_column("problem_statement")