from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import delete, func, select
from src.database.upsert import upsert_rows
from src.database.models import MarketPrice, PortfolioReturn, RegimePrediction, RiskMetric, Trade


class AnalyticsReturnsRepository:
    def _load_stored_returns(
        self,
        portfolio_id: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> pd.Series:
        query = (
            self.db.query(PortfolioReturn)
            .filter(PortfolioReturn.portfolio_id == portfolio_id)
            .order_by(PortfolioReturn.date)
        )
        if start_date is not None:
            query = query.filter(PortfolioReturn.date >= start_date)
        if end_date is not None:
            query = query.filter(PortfolioReturn.date <= end_date)
        rows = query.all()
        if not rows:
            return pd.Series(dtype=float, name="daily_return")
        return pd.Series(
            [row.daily_return for row in rows],
            index=pd.to_datetime([row.date for row in rows]),
            name="daily_return",
            dtype=float,
        )

    def _persist_returns(self, portfolio_id: int, returns: pd.Series) -> None:
        self._remove_pretrade_snapshots(PortfolioReturn, portfolio_id)
        cumulative = (1 + returns).cumprod() - 1
        rows = []
        for row_date, value in returns.items():
            rows.append({
                "portfolio_id": portfolio_id,
                "date": self._to_date(row_date),
                "daily_return": float(value),
                "cumulative_return": float(cumulative.loc[row_date]),
                "portfolio_value": float(1 + cumulative.loc[row_date]),
            })
        upsert_rows(
            self.db,
            PortfolioReturn,
            rows,
            conflict_columns=("portfolio_id", "date"),
            update_columns=("daily_return", "cumulative_return", "portfolio_value"),
        )

    def _persist_latest_risk_metric(self, portfolio_id: int, returns: pd.Series, metrics: dict) -> None:
        metric_date = self._to_date(returns.index.max())
        payload = {
            "portfolio_id": portfolio_id,
            "date": metric_date,
            "historical_var": metrics["historical_var"],
            "parametric_var": metrics["parametric_var"],
            "historical_cvar": metrics["historical_cvar"],
            "parametric_cvar": metrics["parametric_cvar"],
            "sharpe": metrics["sharpe"],
            "sortino": metrics["sortino"],
            "drawdown": metrics["max_drawdown"],
            "volatility": metrics["annualized_volatility"],
            "health_score": self._health_score(metrics),
        }
        upsert_rows(
            self.db,
            RiskMetric,
            [payload],
            conflict_columns=("portfolio_id", "date"),
            update_columns=tuple(
                key for key in payload if key not in {"portfolio_id", "date"}
            ),
        )

    def _persist_regime_predictions(self, portfolio_id: int, history: list[dict]) -> None:
        if not history:
            return
        self._remove_pretrade_snapshots(RegimePrediction, portfolio_id)
        rows = [
            {
                "portfolio_id": portfolio_id,
                "date": record["date"],
                "hidden_state": record["hidden_state"],
                "regime_label": record["regime_label"],
                "probability": record["probability"],
            }
            for record in history
        ]
        upsert_rows(
            self.db,
            RegimePrediction,
            rows,
            conflict_columns=("portfolio_id", "date"),
            update_columns=("hidden_state", "regime_label", "probability"),
        )

    def _remove_pretrade_snapshots(self, model: type, portfolio_id: int) -> None:
        first_trade_date = self.db.scalar(
            select(func.min(Trade.transaction_date)).where(
                Trade.portfolio_id == portfolio_id
            )
        )
        if first_trade_date is None:
            return
        self.db.execute(
            delete(model).where(
                model.portfolio_id == portfolio_id,
                model.date <= first_trade_date,
            )
        )

    def _load_price_frame(self, tickers: list[str], start_date: date, end_date: Optional[date]) -> pd.DataFrame:
        query = (
            self.db.query(MarketPrice)
            .filter(MarketPrice.ticker.in_(tickers), MarketPrice.date >= start_date)
            .order_by(MarketPrice.date)
        )
        if not getattr(self, "include_demo_market_data", False):
            query = query.filter(MarketPrice.data_source != "demo")
        if end_date is not None:
            query = query.filter(MarketPrice.date <= end_date)
        rows = query.all()
        frame = pd.DataFrame(
            [{"date": row.date, "ticker": row.ticker, "close": row.close} for row in rows]
        )
        if frame.empty:
            return pd.DataFrame()
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.pivot(index="date", columns="ticker", values="close").dropna(how="any")

    def _latest_close(self, ticker: str) -> Optional[float]:
        row = (
            self.db.query(MarketPrice)
            .filter(MarketPrice.ticker == ticker)
            .order_by(MarketPrice.date.desc())
        )
        if not getattr(self, "include_demo_market_data", False):
            row = row.filter(MarketPrice.data_source != "demo")
        row = row.first()
        return float(row.close) if row is not None else None
