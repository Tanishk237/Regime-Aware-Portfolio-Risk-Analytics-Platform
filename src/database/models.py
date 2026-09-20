from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    portfolios: Mapped[List["Portfolio"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def is_guest(self) -> bool:
        return self.password_hash is None and self.email.endswith("@guest.latent.local")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_currency: Mapped[str] = mapped_column(String(12), nullable=False, default="INR")
    benchmark: Mapped[str] = mapped_column(String(64), nullable=False, default="NIFTY50")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="portfolios")
    trades: Mapped[List["Trade"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="Trade.transaction_date",
    )
    positions: Mapped[List["Position"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )
    returns: Mapped[List["PortfolioReturn"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="PortfolioReturn.date",
    )


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("transaction_type IN ('BUY', 'SELL')", name="ck_trades_transaction_type"),
        CheckConstraint("quantity > 0", name="ck_trades_quantity_positive"),
        CheckConstraint("price > 0", name="ck_trades_price_positive"),
        CheckConstraint("fees >= 0", name="ck_trades_fees_non_negative"),
        CheckConstraint("taxes >= 0", name="ck_trades_taxes_non_negative"),
        Index("ix_trades_portfolio_ticker", "portfolio_id", "ticker"),
        Index("ix_trades_portfolio_transaction_date", "portfolio_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(8), nullable=False, default="BUY")
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    broker: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fees: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    taxes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="INR")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    portfolio: Mapped["Portfolio"] = relationship(back_populates="trades")


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker", name="uq_positions_portfolio_ticker"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False)
    cost_basis: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    portfolio: Mapped["Portfolio"] = relationship(back_populates="positions")


class PortfolioReturn(Base):
    __tablename__ = "portfolio_returns"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "date", name="uq_portfolio_returns_portfolio_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    daily_return: Mapped[float] = mapped_column(Float, nullable=False)
    cumulative_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    portfolio_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolio: Mapped["Portfolio"] = relationship(back_populates="returns")


class RiskMetric(Base):
    __tablename__ = "risk_metrics"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "date", name="uq_risk_metrics_portfolio_date"),
        Index("ix_risk_metrics_portfolio_date", "portfolio_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    historical_var: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parametric_var: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    historical_cvar: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parametric_cvar: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sortino: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    health_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegimePrediction(Base):
    __tablename__ = "regime_predictions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "date", name="uq_regime_predictions_portfolio_date"),
        Index("ix_regime_predictions_portfolio_date", "portfolio_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hidden_state: Mapped[int] = mapped_column(Integer, nullable=False)
    regime_label: Mapped[str] = mapped_column(String(64), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_portfolio_date", "portfolio_id", "date"),
        UniqueConstraint("portfolio_id", "fingerprint", name="uq_recommendations_portfolio_fingerprint"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RiskProfile(Base):
    __tablename__ = "risk_profiles"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tolerance: Mapped[str] = mapped_column(String(32), nullable=False, default="moderate")
    horizon_months: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_drawdown_tolerance: Mapped[float] = mapped_column(Float, nullable=False, default=0.20)
    liquidity_needs: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    income_requirement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    restrictions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioAlert(Base):
    __tablename__ = "portfolio_alerts"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "fingerprint", name="uq_portfolio_alerts_fingerprint"),
        Index("ix_portfolio_alerts_portfolio_detected", "portfolio_id", "detected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class StressResult(Base):
    __tablename__ = "stress_results"
    __table_args__ = (
        Index("ix_stress_results_portfolio_created_at", "portfolio_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    portfolio_value_before: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    portfolio_value_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_before: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    risk_after: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIReport(Base):
    __tablename__ = "ai_reports"
    __table_args__ = (
        Index("ix_ai_reports_user_created", "user_id", "created_at"),
        Index("ix_ai_reports_portfolio_created", "portfolio_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    response_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="local", server_default="local"
    )
    data_as_of: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RateLimitWindow(Base):
    __tablename__ = "rate_limit_windows"
    __table_args__ = (
        UniqueConstraint(
            "bucket",
            "identity_hash",
            "window_start",
            name="uq_rate_limit_window",
        ),
        Index("ix_rate_limit_windows_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_market_prices_ticker_date"),
        Index("ix_market_prices_ticker_date", "ticker", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    data_source: Mapped[str] = mapped_column(String(32), nullable=False, default="provider", server_default="provider")


class InstrumentMetadata(Base):
    __tablename__ = "instrument_metadata"
    __table_args__ = (UniqueConstraint("ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    data_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="provider", server_default="provider"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VIXHistory(Base):
    __tablename__ = "vix_history"
    __table_args__ = (UniqueConstraint("date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vix: Mapped[float] = mapped_column(Float, nullable=False)


class FIIDIIHistory(Base):
    __tablename__ = "fii_dii_history"
    __table_args__ = (UniqueConstraint("date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fii: Mapped[float] = mapped_column(Float, nullable=False)
    dii: Mapped[float] = mapped_column(Float, nullable=False)
    net_flow: Mapped[float] = mapped_column(Float, nullable=False)


class MarketFeature(Base):
    __tablename__ = "market_features"
    __table_args__ = (UniqueConstraint("date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vix: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vix_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
