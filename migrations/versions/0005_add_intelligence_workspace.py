"""add intelligence workspace

Revision ID: 0005_add_intelligence_workspace
Revises: 0004_add_market_price_data_source
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_add_intelligence_workspace"
down_revision: Union[str, None] = "0004_add_market_price_data_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.add_column(sa.Column("fingerprint", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("evidence", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("action", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("expected_impact", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("confidence", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column("is_read", sa.Boolean(), server_default=sa.text("0"), nullable=False)
        )
        batch_op.add_column(sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint(
            "uq_recommendations_portfolio_fingerprint",
            ["portfolio_id", "fingerprint"],
        )

    op.create_table(
        "risk_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tolerance", sa.String(length=32), nullable=False),
        sa.Column("horizon_months", sa.Integer(), nullable=False),
        sa.Column("max_drawdown_tolerance", sa.Float(), nullable=False),
        sa.Column("liquidity_needs", sa.String(length=32), nullable=False),
        sa.Column("income_requirement", sa.Text(), nullable=True),
        sa.Column("restrictions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_risk_profiles_id", "risk_profiles", ["id"])
    op.create_index("ix_risk_profiles_user_id", "risk_profiles", ["user_id"])

    op.create_table(
        "portfolio_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column(
            "is_read", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "portfolio_id", "fingerprint", name="uq_portfolio_alerts_fingerprint"
        ),
    )
    op.create_index("ix_portfolio_alerts_id", "portfolio_alerts", ["id"])
    op.create_index("ix_portfolio_alerts_portfolio_id", "portfolio_alerts", ["portfolio_id"])
    op.create_index(
        "ix_portfolio_alerts_portfolio_detected",
        "portfolio_alerts",
        ["portfolio_id", "detected_at"],
    )

    op.create_table(
        "ai_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column(
            "response_mode",
            sa.String(length=32),
            server_default="local",
            nullable=False,
        ),
        sa.Column("data_as_of", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_reports_id", "ai_reports", ["id"])
    op.create_index("ix_ai_reports_user_id", "ai_reports", ["user_id"])
    op.create_index("ix_ai_reports_portfolio_id", "ai_reports", ["portfolio_id"])
    op.create_index("ix_ai_reports_user_created", "ai_reports", ["user_id", "created_at"])
    op.create_index(
        "ix_ai_reports_portfolio_created",
        "ai_reports",
        ["portfolio_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("ai_reports")
    op.drop_table("portfolio_alerts")
    op.drop_table("risk_profiles")
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.drop_constraint(
            "uq_recommendations_portfolio_fingerprint", type_="unique"
        )
        batch_op.drop_column("read_at")
        batch_op.drop_column("is_read")
        batch_op.drop_column("confidence")
        batch_op.drop_column("expected_impact")
        batch_op.drop_column("action")
        batch_op.drop_column("evidence")
        batch_op.drop_column("fingerprint")
