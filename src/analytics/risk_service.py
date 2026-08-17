from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.api.errors import AppError
from src.database.models import User
from src.portfolio.portfolio_service import PortfolioService


class AnalyticsRiskService:
    PARAMETRIC_Z_SCORES = {
        0.90: 1.2815515655446004,
        0.95: 1.6448536269514722,
        0.99: 2.3263478740408408,
    }

    def _calculate_risk_metrics(
        self,
        returns: pd.Series,
        *,
        confidence_level: float,
        risk_free_rate: float,
    ) -> dict:
        clean = returns.dropna().astype(float)
        if len(clean) < 2:
            raise AppError(
                "At least two return observations are required.",
                code="INSUFFICIENT_RETURNS",
                status_code=422,
            )

        daily_rf = risk_free_rate / 252
        std = float(clean.std())
        mean = float(clean.mean())
        historical_var = float(np.quantile(clean, 1 - confidence_level))
        historical_cvar = float(clean[clean <= historical_var].mean())
        z_score = self.PARAMETRIC_Z_SCORES.get(round(confidence_level, 2), 1.6448536269514722)
        parametric_var = float(mean - z_score * std)
        parametric_cvar = float(mean - std * self._normal_pdf(z_score) / (1 - confidence_level))
        excess = clean - daily_rf
        sharpe = self._safe_div(float(excess.mean() * math.sqrt(252)), std)
        downside_std = float(excess[excess < 0].std())
        sortino = self._safe_div(float(excess.mean() * math.sqrt(252)), downside_std)
        cumulative = (1 + clean).cumprod()
        drawdown = cumulative / cumulative.cummax() - 1
        max_drawdown = float(drawdown.min())
        annualized_volatility = float(std * math.sqrt(252))
        total_return = float(cumulative.iloc[-1] - 1)
        years = max(len(clean) / 252, 1 / 252)
        cagr = float((1 + total_return) ** (1 / years) - 1) if total_return > -1 else -1.0
        calmar = self._safe_div(cagr, abs(max_drawdown))

        return {
            "daily_mean_return": mean,
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
        cumulative = (1 + returns).cumprod()
        drawdown = cumulative / cumulative.cummax() - 1
        rolling_returns = returns.rolling(rolling_window).apply(lambda values: (1 + values).prod() - 1)
        rolling_volatility = returns.rolling(rolling_window).std() * math.sqrt(252)

        return {
            "cumulative_returns": self._series_to_records(cumulative - 1, "cumulative_return"),
            "rolling_returns": self._series_to_records(rolling_returns.dropna(), "rolling_return"),
            "drawdown": self._series_to_records(drawdown, "drawdown"),
            "rolling_volatility": self._series_to_records(rolling_volatility.dropna(), "rolling_volatility"),
        }

    def _build_pnl(self, user: User, portfolio_id: int) -> dict:
        positions = PortfolioService(self.db).list_positions(user, portfolio_id)
        total_cost_basis = float(sum(position.cost_basis for position in positions))
        realized_pnl = float(sum(position.realized_pnl for position in positions))
        position_rows = []
        market_value = 0.0

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
            if position_market_value is not None:
                market_value += position_market_value
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

        return {
            "cost_basis": total_cost_basis,
            "market_value": market_value if position_rows else None,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": market_value - total_cost_basis if position_rows else None,
            "total_pnl": market_value - total_cost_basis + realized_pnl if position_rows else realized_pnl,
            "positions": position_rows,
        }
