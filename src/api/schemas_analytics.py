from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class DatedValue(BaseModel):
    date: date

    model_config = {"extra": "allow"}


class PositionPnL(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: Optional[float] = None
    cost_basis: float
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: float
    pnl_pct: Optional[float] = None


class PortfolioPnL(BaseModel):
    cost_basis: float
    market_value: Optional[float] = None
    realized_pnl: float
    unrealized_pnl: Optional[float] = None
    total_pnl: Optional[float] = None
    positions: list[PositionPnL]


class RiskMetrics(BaseModel):
    daily_mean_return: float
    total_return: float
    cagr: float
    historical_var: float
    parametric_var: float
    historical_cvar: float
    parametric_cvar: float
    sharpe: Optional[float] = None
    sortino: Optional[float] = None
    calmar: Optional[float] = None
    max_drawdown: float
    annualized_volatility: float


class RiskAnalyticsResponse(BaseModel):
    success: bool = True
    portfolio_id: int
    as_of: date
    returns: list[DatedValue]
    pnl: PortfolioPnL
    metrics: RiskMetrics
    series: dict[str, list[DatedValue]]


class RegimeAnalyticsRequest(BaseModel):
    start_date: date
    end_date: Optional[date] = None
    weights: Optional[list[float]] = None

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, value: Optional[list[float]]) -> Optional[list[float]]:
        if value is None:
            return value
        if any(weight < 0 for weight in value):
            raise ValueError("Weights cannot be negative.")
        if sum(value) <= 0:
            raise ValueError("Weights must sum to a positive value.")
        return value


class RegimeHistoryPoint(BaseModel):
    date: date
    hidden_state: int
    regime_label: str
    probability: float


class RegimeStatistic(BaseModel):
    hidden_state: int
    regime_label: str
    sample_count: int
    average_return: Optional[float] = None
    average_volatility: Optional[float] = None
    average_drawdown: Optional[float] = None
    average_vix: Optional[float] = None


class RegimeDuration(BaseModel):
    hidden_state: int
    start_date: date
    end_date: date
    duration_days: int


class RegimeAnalyticsResponse(BaseModel):
    success: bool = True
    portfolio_id: int
    tickers: list[str]
    current_regime: str
    current_state: int
    regime_probability: float
    regime_history: list[RegimeHistoryPoint]
    transition_matrix: list[list[float]]
    regime_statistics: list[RegimeStatistic]
    regime_duration: list[RegimeDuration]
    state_labels: dict[str, str]
    feature_metadata: dict[str, Any]
