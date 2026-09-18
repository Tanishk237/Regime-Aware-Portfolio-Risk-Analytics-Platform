"""add market price data source

Revision ID: 0004_add_market_price_data_source
Revises: 0003_add_portfolio_demo_flag
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_market_price_data_source"
down_revision = "0003_add_portfolio_demo_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_prices",
        sa.Column("data_source", sa.String(length=32), nullable=False, server_default="provider"),
    )


def downgrade() -> None:
    op.drop_column("market_prices", "data_source")
