"""add revocable user token version

Revision ID: 0010_add_user_token_version
Revises: 0009_add_rate_limit_windows
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_add_user_token_version"
down_revision: Union[str, None] = "0009_add_rate_limit_windows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
