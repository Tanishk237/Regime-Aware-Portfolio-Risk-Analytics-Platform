"""add portfolio demo flag

Revision ID: 0003_add_portfolio_demo_flag
Revises: 0002_add_user_password_hash
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_add_portfolio_demo_flag"
down_revision = "0002_add_user_password_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portfolios",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("portfolios", "is_demo")
