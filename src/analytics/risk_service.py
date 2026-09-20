from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

from src.api.errors import AppError
from src.database.models import User
from src.portfolio.portfolio_service import PortfolioService


class AnalyticsRiskService:
    def _calculate_risk_metrics(
        self,
        returns: pd.Series,
        *,
        confidence_level: float,
        risk_free_rate: float,
    ) -> dict:
        if not 0 < confidence_level < 1:
            raise AppError(
                "confidence_level must be between 0 and 1.",
                code="INVALID_CONFIDENCE_LEVEL",
                status_code=422,
            )
        if not math.isfinite(risk_free_rate) or risk_free_rate <= -1:
            raise AppError(
                "risk_free_rate must be finite and greater than -1.",
                code="INVALID_RISK_FREE_RATE",
                status_code=422,
            )

        clean = returns.dropna().astype(float)
        if len(clean) < 2:
            raise AppError(
                "At least two return observations are required.",
                code="INSUFFICIENT_RETURNS",
                status_code=422,
            )

        if not np.isfinite(clean.to_numpy()).all():
            raise AppError(
                "Returns contain non-finite values.",
                code="INVALID_RETURNS",
                status_code=422,
            )
        if (clean <= -1).any():
            raise AppError(
                "Returns cannot be less than or equal to -100%.",
                code="INVALID_RETURNS",
                status_code=422,
            )

        daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
        std = float(clean.std())
        mean = float(clean.mean())
        historical_var = float(np.quantile(clean, 1 - confidence_level))
        historical_cvar = float(clean[clean <= historical_var].mean())
        z_score = NormalDist().inv_cdf(confidence_level)
        parametric_var = float(mean - z_score * std)
        parametric_cvar = float(mean - std * self._normal_pdf(z_score) / (1 - confidence_level))
        excess = clean - daily_rf
        sharpe = self._safe_div(float(excess.mean() * math.sqrt(252)), std)
        downside_deviation = float(np.sqrt(np.mean(np.minimum(excess.to_numpy(), 0.0) ** 2)))
        sortino = self._safe_div(
            float(excess.mean() * math.sqrt(252)),
            downside_deviation,
        )
        cumulative = (1 + clean).cumprod()
        drawdown = self._drawdown_series(cumulative)
        max_drawdown = float(drawdown.min())
        annualized_volatility = float(std * math.sqrt(252))
        total_return = float(cumulative.iloc[-1] - 1)
        years = max(len(clean) / 252, 1 / 252)
        cagr = float((1 + total_return) ** (1 / years) - 1) if total_return > -1 else -1.0
        calmar = self._safe_div(cagr, abs(max_drawdown))

        return {
            "daily_mean_return": mean,
            "period_return": total_return,
            "total_return": total_return,
            "cagr": cagr,
            "historical_var": historical_var,
            "parametric_var": parametric_var,
            "historical_cvar": historical_cvar,
            "parametric_cvar": parametric_cvar,
            "sharpe": sharpe,
            "sortino": sortino,
            "calmar": calmar,
            "max_drawdown": max_drawdown,
            "annualized_volatility": annualized_volatility,
        }

    def _build_risk_series(self, returns: pd.Series, *, rolling_window: int) -> dict:
        clean = returns.dropna().astype(float)
        cumulative = (1 + clean).cumprod()
        drawdown = self._drawdown_series(cumulative)
        rolling_returns = clean.rolling(rolling_window).apply(lambda values: (1 + values).prod() - 1)
        rolling_volatility = clean.rolling(rolling_window).std() * math.sqrt(252)

        return {
            "cumulative_returns": self._series_to_records(cumulative - 1, "cumulative_return"),
            "rolling_returns": self._series_to_records(rolling_returns.dropna(), "rolling_return"),
            "drawdown": self._series_to_records(drawdown, "drawdown"),
            "rolling_volatility": self._series_to_records(rolling_volatility.dropna(), "rolling_volatility"),
        }

    @staticmethod
    def _drawdown_series(cumulative_wealth: pd.Series) -> pd.Series:
        # Starting capital is always a peak, so an immediate loss is a drawdown.
        running_peak = cumulative_wealth.cummax().clip(lower=1.0)
        return cumulative_wealth / running_peak - 1

    def _build_pnl(self, user: User, portfolio_id: int) -> dict:
        positions = PortfolioService(
            self.db,
            market_data_service=self.market_data_service,
        ).list_positions(user, portfolio_id)
        total_cost_basis = float(sum(position.cost_basis for position in positions))
        realized_pnl = float(sum(position.realized_pnl for position in positions))
        position_rows = []
        open_market_values = []

        for position in positions:
            latest_price = self._latest_close(position.ticker)
            current_price = latest_price if latest_price is not None else position.current_price
            position_market_value = (
                float(position.quantity) * float(current_price)
                if current_price is not None
                else None
            )
            unrealized_pnl = (
                position_market_value - float(position.cost_basis)
                if position_market_value is not None
                else float(position.unrealized_pnl)
            )
            if position.quantity > 0:
                open_market_values.append(position_market_value)
            position_rows.append(
                {
                    "ticker": position.ticker,
                    "quantity": float(position.quantity),
                    "avg_cost": float(position.avg_cost),
                    "current_price": current_price,
                    "cost_basis": float(position.cost_basis),
                    "market_value": position_market_value,
                    "unrealized_pnl": unrealized_pnl,
                    "realized_pnl": float(position.realized_pnl),
                    "pnl_pct": self._safe_div(unrealized_pnl, float(position.cost_basis)),
                }
            )

        all_open_positions_valued = bool(open_market_values) and all(
            value is not None for value in open_market_values
        )
        market_value = (
            float(sum(value for value in open_market_values if value is not None))
            if all_open_positions_valued
            else None
        )
        unrealized_pnl = (
            market_value - total_cost_basis
            if market_value is not None
            else None
        )
        total_pnl = (
            unrealized_pnl + realized_pnl
            if unrealized_pnl is not None
            else realized_pnl if not open_market_values else None
        )

        return {
            "cost_basis": total_cost_basis,
            "market_value": market_value,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl,
            "positions": position_rows,
        }
