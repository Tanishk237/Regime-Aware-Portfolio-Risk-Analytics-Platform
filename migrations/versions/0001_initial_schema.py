"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_currency", sa.String(length=12), nullable=False, server_default="INR"),
        sa.Column("benchmark", sa.String(length=64), nullable=False, server_default="NIFTY50"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_portfolios_id", "portfolios", ["id"])
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("transaction_type", sa.String(length=8), nullable=False, server_default="BUY"),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("broker", sa.String(length=255), nullable=True),
        sa.Column("fees", sa.Float(), nullable=False, server_default="0"),
        sa.Column("taxes", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="INR"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("transaction_type IN ('BUY', 'SELL')", name="ck_trades_transaction_type"),
        sa.CheckConstraint("quantity > 0", name="ck_trades_quantity_positive"),
        sa.CheckConstraint("price > 0", name="ck_trades_price_positive"),
        sa.CheckConstraint("fees >= 0", name="ck_trades_fees_non_negative"),
        sa.CheckConstraint("taxes >= 0", name="ck_trades_taxes_non_negative"),
    )
    op.create_index("ix_trades_id", "trades", ["id"])
    op.create_index("ix_trades_portfolio_id", "trades", ["portfolio_id"])
    op.create_index("ix_trades_ticker", "trades", ["ticker"])
    op.create_index("ix_trades_transaction_date", "trades", ["transaction_date"])
    op.create_index("ix_trades_portfolio_ticker", "trades", ["portfolio_id", "ticker"])
    op.create_index("ix_trades_portfolio_transaction_date", "trades", ["portfolio_id", "transaction_date"])

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("avg_cost", sa.Float(), nullable=False),
        sa.Column("cost_basis", sa.Float(), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("market_value", sa.Float(), nullable=True),
        sa.Column("market_weight", sa.Float(), nullable=True),
        sa.Column("cost_weight", sa.Float(), nullable=True),
        sa.Column("unrealized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("portfolio_id", "ticker", name="uq_positions_portfolio_ticker"),
    )
    op.create_index("ix_positions_id", "positions", ["id"])
    op.create_index("ix_positions_portfolio_id", "positions", ["portfolio_id"])
    op.create_index("ix_positions_ticker", "positions", ["ticker"])

    op.create_table(
        "portfolio_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("daily_return", sa.Float(), nullable=False),
        sa.Column("cumulative_return", sa.Float(), nullable=True),
        sa.Column("portfolio_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("portfolio_id", "date", name="uq_portfolio_returns_portfolio_date"),
    )
    op.create_index("ix_portfolio_returns_id", "portfolio_returns", ["id"])
    op.create_index("ix_portfolio_returns_portfolio_id", "portfolio_returns", ["portfolio_id"])
    op.create_index("ix_portfolio_returns_date", "portfolio_returns", ["date"])

    op.create_table(
        "risk_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("historical_var", sa.Float(), nullable=True),
        sa.Column("parametric_var", sa.Float(), nullable=True),
        sa.Column("historical_cvar", sa.Float(), nullable=True),
        sa.Column("parametric_cvar", sa.Float(), nullable=True),
        sa.Column("sharpe", sa.Float(), nullable=True),
        sa.Column("sortino", sa.Float(), nullable=True),
        sa.Column("drawdown", sa.Float(), nullable=True),
        sa.Column("volatility", sa.Float(), nullable=True),
        sa.Column("health_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("portfolio_id", "date", name="uq_risk_metrics_portfolio_date"),
    )
    op.create_index("ix_risk_metrics_id", "risk_metrics", ["id"])
    op.create_index("ix_risk_metrics_portfolio_id", "risk_metrics", ["portfolio_id"])
    op.create_index("ix_risk_metrics_date", "risk_metrics", ["date"])
    op.create_index("ix_risk_metrics_portfolio_date", "risk_metrics", ["portfolio_id", "date"])

    op.create_table(
        "regime_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("hidden_state", sa.Integer(), nullable=False),
        sa.Column("regime_label", sa.String(length=64), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("portfolio_id", "date", name="uq_regime_predictions_portfolio_date"),
    )
    op.create_index("ix_regime_predictions_id", "regime_predictions", ["id"])
    op.create_index("ix_regime_predictions_portfolio_id", "regime_predictions", ["portfolio_id"])
    op.create_index("ix_regime_predictions_date", "regime_predictions", ["date"])
    op.create_index("ix_regime_predictions_portfolio_date", "regime_predictions", ["portfolio_id", "date"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recommendations_id", "recommendations", ["id"])
    op.create_index("ix_recommendations_portfolio_id", "recommendations", ["portfolio_id"])
    op.create_index("ix_recommendations_date", "recommendations", ["date"])
    op.create_index("ix_recommendations_portfolio_date", "recommendations", ["portfolio_id", "date"])

    op.create_table(
        "stress_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_name", sa.String(length=255), nullable=False),
        sa.Column("scenario_parameters", sa.JSON(), nullable=False),
        sa.Column("portfolio_value_before", sa.Float(), nullable=True),
        sa.Column("portfolio_value_after", sa.Float(), nullable=True),
        sa.Column("risk_before", sa.JSON(), nullable=True),
        sa.Column("risk_after", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_stress_results_id", "stress_results", ["id"])
    op.create_index("ix_stress_results_portfolio_id", "stress_results", ["portfolio_id"])
    op.create_index("ix_stress_results_portfolio_created_at", "stress_results", ["portfolio_id", "created_at"])

    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.UniqueConstraint("ticker", "date", name="uq_market_prices_ticker_date"),
    )
    op.create_index("ix_market_prices_id", "market_prices", ["id"])
    op.create_index("ix_market_prices_ticker", "market_prices", ["ticker"])
    op.create_index("ix_market_prices_date", "market_prices", ["date"])
    op.create_index("ix_market_prices_ticker_date", "market_prices", ["ticker", "date"])

    op.create_table(
        "vix_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, unique=True),
        sa.Column("vix", sa.Float(), nullable=False),
    )
    op.create_index("ix_vix_history_id", "vix_history", ["id"])
    op.create_index("ix_vix_history_date", "vix_history", ["date"])

    op.create_table(
        "fii_dii_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, unique=True),
        sa.Column("fii", sa.Float(), nullable=False),
        sa.Column("dii", sa.Float(), nullable=False),
        sa.Column("net_flow", sa.Float(), nullable=False),
    )
    op.create_index("ix_fii_dii_history_id", "fii_dii_history", ["id"])
    op.create_index("ix_fii_dii_history_date", "fii_dii_history", ["date"])

    op.create_table(
        "market_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, unique=True),
        sa.Column("vix", sa.Float(), nullable=True),
        sa.Column("vix_change", sa.Float(), nullable=True),
        sa.Column("net_flow", sa.Float(), nullable=True),
        sa.Column("volatility", sa.Float(), nullable=True),
        sa.Column("market_return", sa.Float(), nullable=True),
    )
    op.create_index("ix_market_features_id", "market_features", ["id"])
    op.create_index("ix_market_features_date", "market_features", ["date"])


def downgrade() -> None:
    op.drop_table("market_features")
    op.drop_table("fii_dii_history")
    op.drop_table("vix_history")
    op.drop_table("market_prices")
    op.drop_table("stress_results")
    op.drop_table("recommendations")
    op.drop_table("regime_predictions")
    op.drop_table("risk_metrics")
    op.drop_table("portfolio_returns")
    op.drop_table("positions")
    op.drop_table("trades")
    op.drop_table("portfolios")
    op.drop_table("users")
