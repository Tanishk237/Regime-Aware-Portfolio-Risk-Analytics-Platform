from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import delete

from src.database.models import MarketPrice, PortfolioReturn, RegimePrediction, RiskMetric


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
        cumulative = (1 + returns).cumprod() - 1
        for row_date, value in returns.items():
            row_day = self._to_date(row_date)
            existing = (
                self.db.query(PortfolioReturn)
                .filter(PortfolioReturn.portfolio_id == portfolio_id, PortfolioReturn.date == row_day)
                .one_or_none()
            )
            payload = {
                "daily_return": float(value),
                "cumulative_return": float(cumulative.loc[row_date]),
                "portfolio_value": float(1 + cumulative.loc[row_date]),
            }
            if existing is None:
                self.db.add(PortfolioReturn(portfolio_id=portfolio_id, date=row_day, **payload))
            else:
                for key, item in payload.items():
                    setattr(existing, key, item)
        self.db.commit()

    def _persist_latest_risk_metric(self, portfolio_id: int, returns: pd.Series, metrics: dict) -> None:
        metric_date = self._to_date(returns.index.max())
        existing = (
            self.db.query(RiskMetric)
            .filter(RiskMetric.portfolio_id == portfolio_id, RiskMetric.date == metric_date)
            .one_or_none()
        )
        payload = {
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
        if existing is None:
            self.db.add(RiskMetric(portfolio_id=portfolio_id, date=metric_date, **payload))
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
        self.db.commit()

    def _persist_regime_predictions(self, portfolio_id: int, history: list[dict]) -> None:
        if not history:
            return
        dates = [record["date"] for record in history]
        self.db.execute(
            delete(RegimePrediction).where(
                RegimePrediction.portfolio_id == portfolio_id,
                RegimePrediction.date.in_(dates),
            )
        )
        for record in history:
            self.db.add(
                RegimePrediction(
                    portfolio_id=portfolio_id,
                    date=record["date"],
                    hidden_state=record["hidden_state"],
                    regime_label=record["regime_label"],
                    probability=record["probability"],
                )
            )
        self.db.commit()

    def _load_price_frame(self, tickers: list[str], start_date: date, end_date: Optional[date]) -> pd.DataFrame:
        query = (
            self.db.query(MarketPrice)
            .filter(MarketPrice.ticker.in_(tickers), MarketPrice.date >= start_date)
            .order_by(MarketPrice.date)
        )
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
            .first()
        )
        return float(row.close) if row is not None else None
