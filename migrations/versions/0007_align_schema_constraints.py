"""align intelligence timestamp constraints

Revision ID: 0007_align_schema_constraints
Revises: 0006_add_instrument_metadata
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_align_schema_constraints"
down_revision: Union[str, None] = "0006_add_instrument_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table_name, column_names in (
        ("risk_profiles", ("created_at", "updated_at")),
        ("portfolio_alerts", ("detected_at",)),
        ("ai_reports", ("created_at",)),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                batch_op.alter_column(
                    column_name,
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False,
                )


def downgrade() -> None:
    for table_name, column_names in (
        ("risk_profiles", ("created_at", "updated_at")),
        ("portfolio_alerts", ("detected_at",)),
        ("ai_reports", ("created_at",)),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                batch_op.alter_column(
                    column_name,
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True,
                )
