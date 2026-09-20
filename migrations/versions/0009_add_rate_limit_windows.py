"""add durable API rate limit windows

Revision ID: 0009_add_rate_limit_windows
Revises: 0008_remove_pretrade_snapshots
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_add_rate_limit_windows"
down_revision: Union[str, None] = "0008_remove_pretrade_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_windows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bucket", sa.String(length=64), nullable=False),
        sa.Column("identity_hash", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bucket",
            "identity_hash",
            "window_start",
            name="uq_rate_limit_window",
        ),
    )
    op.create_index(
        "ix_rate_limit_windows_expires_at",
        "rate_limit_windows",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_windows_expires_at", table_name="rate_limit_windows")
    op.drop_table("rate_limit_windows")
