"""remove derived snapshots before portfolio inception

Revision ID: 0008_remove_pretrade_snapshots
Revises: 0007_align_schema_constraints
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0008_remove_pretrade_snapshots"
down_revision: Union[str, None] = "0007_align_schema_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table_name in ("portfolio_returns", "risk_metrics", "regime_predictions"):
        op.execute(
            f"""
            DELETE FROM {table_name}
            WHERE date <= (
                SELECT MIN(trades.transaction_date)
                FROM trades
                WHERE trades.portfolio_id = {table_name}.portfolio_id
            )
            """
        )


def downgrade() -> None:
    # Derived snapshots are reproducible from trades and market data.
    pass
