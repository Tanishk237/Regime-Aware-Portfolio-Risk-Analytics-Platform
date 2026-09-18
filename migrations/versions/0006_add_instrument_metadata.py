"""add instrument metadata

Revision ID: 0006_add_instrument_metadata
Revises: 0005_add_intelligence_workspace
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_add_instrument_metadata"
down_revision: Union[str, None] = "0005_add_intelligence_workspace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instrument_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("sector", sa.String(length=128), nullable=True),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("exchange", sa.String(length=64), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=12), nullable=True),
        sa.Column(
            "data_source",
            sa.String(length=32),
            server_default="provider",
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
    )
    op.create_index("ix_instrument_metadata_id", "instrument_metadata", ["id"])
    op.create_index("ix_instrument_metadata_ticker", "instrument_metadata", ["ticker"])


def downgrade() -> None:
    op.drop_table("instrument_metadata")
