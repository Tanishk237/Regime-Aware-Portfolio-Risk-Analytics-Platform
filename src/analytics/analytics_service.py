from __future__ import annotations

import math
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.database.models import (
    MarketPrice,
    Portfolio,
    PortfolioReturn,
    Position,
    RegimePrediction,
    RiskMetric,
    User,
)
from src.market import MarketDataService
from src.portfolio.portfolio_service import PortfolioService
from src.regime.predict_regime import RegimePredictor
from src.regime.probability_engine import RegimeProbabilityEngine


class AnalyticsService:
    PARAMETRIC_Z_SCORES = {
        0.90: 1.2815515655446004,
        0.95: 1.6448536269514722,
        0.99: 2.3263478740408408,
    }

    def __init__(
        self,
        db: Session,
        *,
        market_data_service: Optional[MarketDataService] = None,
        model_dir: str = "models",
    ):
        self.db = db
        self.market_data_service = market_data_service or MarketDataService(db)
        self.model_dir = model_dir

    def build_risk_payload(
        self,
        user: User,
        portfolio_id: int,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        confidence_level: float = 0.95,
        risk_free_rate: float = 0.06,
        rolling_window: int = 20,
        persist: bool = True,
    ) -> dict:
        self._validate_date_range(start_date, end_date)
        portfolio = PortfolioService(self.db).get_portfolio(user, portfolio_id)
        returns = self.get_or_build_returns(
            user,
            portfolio,
            start_date=start_date,
            end_date=end_date,
            persist=persist,
        )
        if returns.empty:
            raise AppError(
                "Portfolio returns are not available for analytics.",
                code="PORTFOLIO_RETURNS_EMPTY",
                status_code=404,
            )

        pnl = self._build_pnl(user, portfolio.id)
        metrics = self._calculate_risk_metrics(
            returns,
            confidence_level=confidence_level,
            risk_free_rate=risk_free_rate,
        )
        series = self._build_risk_series(returns, rolling_window=rolling_window)

        if persist:
            self._persist_returns(portfolio.id, returns)
            self._persist_latest_risk_metric(portfolio.id, returns, metrics)

        return {
            "portfolio_id": portfolio.id,
            "as_of": returns.index.max().date(),
            "returns": self._series_to_records(returns, "daily_return"),
            "pnl": pnl,
            "metrics": metrics,
            "series": series,
        }

    def build_regime_payload(
        self,
        user: User,
        portfolio_id: int,
        *,
        start_date: date,
        end_date: Optional[date] = None,
        weights: Optional[list[float]] = None,
        persist: bool = True,
    ) -> dict:
        self._validate_date_range(start_date, end_date)
        portfolio = PortfolioService(self.db).get_portfolio(user, portfolio_id)
        positions = PortfolioService(self.db).list_positions(user, portfolio.id)
        tickers = [position.ticker for position in positions if position.quantity > 0]
        if not tickers:
            raise AppError(
                "Portfolio has no open positions for regime analytics.",
                code="PORTFOLIO_POSITIONS_EMPTY",
                status_code=400,
            )

        if weights is None:
            weights = self._weights_from_positions(positions)

        feature_payload = self.market_data_service.build_feature_matrix(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            weights=weights,
            persist=persist,
        )
        feature_matrix = self._feature_records_to_frame(feature_payload["records"])
        regime_payload = self._predict_regimes(feature_matrix)

        if persist:
            self._persist_regime_predictions(portfolio.id, regime_payload["history"])

        return {
            "portfolio_id": portfolio.id,
            "tickers": tickers,
            "current_regime": regime_payload["current_regime"],
            "current_state": regime_payload["current_state"],
            "regime_probability": regime_payload["regime_probability"],
            "regime_history": regime_payload["history"],
            "transition_matrix": regime_payload["transition_matrix"],
            "regime_statistics": regime_payload["statistics"],
            "regime_duration": regime_payload["duration"],
            "state_labels": regime_payload["state_labels"],
            "feature_metadata": feature_payload["metadata"],
        }

    def get_or_build_returns(
        self,
        user: User,
        portfolio: Portfolio,
        *,
        start_date: Optional[date],
        end_date: Optional[date],
        persist: bool,
    ) -> pd.Series:
        stored = self._load_stored_returns(portfolio.id, start_date, end_date)
        if not stored.empty:
            return stored

        positions = PortfolioService(self.db).list_positions(user, portfolio.id)
        open_positions = [position for position in positions if position.quantity > 0]
        if not open_positions:
            raise AppError(
                "Portfolio has no open positions for return analytics.",
                code="PORTFOLIO_POSITIONS_EMPTY",
                status_code=400,
            )

        if start_date is None:
            start_date = portfolio.created_at.date()

        tickers = [position.ticker for position in open_positions]
        self.market_data_service.get_historical_prices(
            tickers,
            start_date,
            end_date,
            persist=True,
        )
        prices = self._load_price_frame(tickers, start_date, end_date)
        if prices.empty or len(prices) < 2:
            raise AppError(
                "Not enough market price data to calculate portfolio returns.",
                code="INSUFFICIENT_MARKET_DATA",
                status_code=404,
            )

        weights = pd.Series(
            self._weights_from_positions(open_positions),
            index=tickers,
            dtype=float,
        )
        returns = prices.pct_change().dropna().mul(weights, axis=1).sum(axis=1)
        returns.name = "daily_return"

        if persist:
            self._persist_returns(portfolio.id, returns)

        return returns

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

    def _predict_regimes(self, feature_matrix: pd.DataFrame) -> dict:
        try:
            predictor = RegimePredictor(model_dir=self.model_dir)
            probabilities = RegimeProbabilityEngine(model_dir=self.model_dir).probability_dataframe(feature_matrix)
            prediction_df = predictor.build_prediction_dataframe(feature_matrix)
            transition_matrix = predictor.transition_matrix()
            state_labels = predictor.state_labels
        except Exception:
            prediction_df, probabilities, transition_matrix, state_labels = self._fallback_regime_prediction(feature_matrix)

        history = []
        for row_date, row in prediction_df.iterrows():
            state = int(row["state"])
            label = str(row["state_label"])
            probability = float(probabilities.loc[row_date].max())
            history.append(
                {
                    "date": self._to_date(row_date),
                    "hidden_state": state,
                    "regime_label": label,
                    "probability": probability,
                }
            )

        current = history[-1]
        return {
            "current_regime": current["regime_label"],
            "current_state": current["hidden_state"],
            "regime_probability": current["probability"],
            "history": history,
            "transition_matrix": self._dataframe_to_matrix(transition_matrix),
            "statistics": self._regime_statistics(feature_matrix, prediction_df),
            "duration": self._regime_duration(prediction_df["state"]),
            "state_labels": {str(key): value for key, value in state_labels.items()},
        }

    def _fallback_regime_prediction(self, feature_matrix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[int, str]]:
        volatility_column = "volatility_20" if "volatility_20" in feature_matrix.columns else None
        return_column = "portfolio_return" if "portfolio_return" in feature_matrix.columns else None
        vix_column = "vix" if "vix" in feature_matrix.columns else None
        volatility_threshold = feature_matrix[volatility_column].quantile(0.75) if volatility_column else None
        return_threshold = feature_matrix[return_column].quantile(0.4) if return_column else None
        vix_threshold = feature_matrix[vix_column].quantile(0.75) if vix_column else None

        states = []
        labels = []
        for _, row in feature_matrix.iterrows():
            if volatility_column and row[volatility_column] >= volatility_threshold:
                state, label = 2, "High Volatility"
            elif vix_column and row[vix_column] >= vix_threshold:
                state, label = 2, "High Volatility"
            elif return_column and row[return_column] < return_threshold:
                state, label = 1, "Bear"
            else:
                state, label = 0, "Bull"
            states.append(state)
            labels.append(label)

        prediction_df = pd.DataFrame(
            {"state": states, "state_label": labels},
            index=feature_matrix.index,
        )
        state_labels = {0: "Bull", 1: "Bear", 2: "High Volatility"}
        probabilities = pd.DataFrame(0.05, index=feature_matrix.index, columns=list(state_labels.values()))
        for row_date, label in zip(feature_matrix.index, labels):
            probabilities.loc[row_date, label] = 0.90

        transition_matrix = self._estimate_transition_matrix(pd.Series(states), state_count=3)
        return prediction_df, probabilities, transition_matrix, state_labels

    def _regime_statistics(self, feature_matrix: pd.DataFrame, prediction_df: pd.DataFrame) -> list[dict]:
        frame = feature_matrix.copy()
        frame["hidden_state"] = prediction_df["state"].astype(int)
        frame["regime_label"] = prediction_df["state_label"]
        rows = []
        for (state, label), group in frame.groupby(["hidden_state", "regime_label"]):
            rows.append(
                {
                    "hidden_state": int(state),
                    "regime_label": str(label),
                    "sample_count": int(len(group)),
                    "average_return": self._optional_float(group.get("portfolio_return", pd.Series(dtype=float)).mean()),
                    "average_volatility": self._optional_float(group.get("volatility_20", pd.Series(dtype=float)).mean()),
                    "average_drawdown": self._optional_float(group.get("drawdown", pd.Series(dtype=float)).mean()),
                    "average_vix": self._optional_float(group.get("vix", pd.Series(dtype=float)).mean()),
                }
            )
        return rows

    def _regime_duration(self, states: pd.Series) -> list[dict]:
        rows = []
        previous_state = None
        start = None
        duration = 0
        previous_date = None
        for row_date, state in states.items():
            state = int(state)
            if previous_state is None:
                previous_state = state
                start = row_date
                duration = 1
                previous_date = row_date
                continue
            if state == previous_state:
                duration += 1
                previous_date = row_date
                continue
            rows.append(
                {
                    "hidden_state": int(previous_state),
                    "start_date": self._to_date(start),
                    "end_date": self._to_date(previous_date),
                    "duration_days": duration,
                }
            )
            previous_state = state
            start = row_date
            duration = 1
            previous_date = row_date
        if previous_state is not None:
            rows.append(
                {
                    "hidden_state": int(previous_state),
                    "start_date": self._to_date(start),
                    "end_date": self._to_date(states.index[-1]),
                    "duration_days": duration,
                }
            )
        return rows

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
        series = pd.Series(
            [row.daily_return for row in rows],
            index=pd.to_datetime([row.date for row in rows]),
            name="daily_return",
            dtype=float,
        )
        return series

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

    @staticmethod
    def _weights_from_positions(positions: list[Position]) -> list[float]:
        cost_basis = [float(position.cost_basis) for position in positions if position.quantity > 0]
        total = sum(cost_basis)
        if not total:
            return [1 / len(cost_basis)] * len(cost_basis)
        return [value / total for value in cost_basis]

    @staticmethod
    def _feature_records_to_frame(records: list[dict]) -> pd.DataFrame:
        frame = pd.DataFrame(
            [{"date": record["date"], **record["values"]} for record in records]
        )
        if frame.empty:
            return pd.DataFrame()
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.set_index("date").sort_index()

    @staticmethod
    def _series_to_records(series: pd.Series, value_name: str) -> list[dict]:
        return [
            {
                "date": pd.Timestamp(row_date).date(),
                value_name: float(value),
            }
            for row_date, value in series.dropna().items()
        ]

    @staticmethod
    def _dataframe_to_matrix(frame: pd.DataFrame) -> list[list[float]]:
        return [[float(value) for value in row] for row in frame.values]

    @staticmethod
    def _estimate_transition_matrix(states: pd.Series, state_count: int) -> pd.DataFrame:
        matrix = np.zeros((state_count, state_count), dtype=float)
        values = states.astype(int).tolist()
        for current, nxt in zip(values, values[1:]):
            matrix[current, nxt] += 1
        for state in range(state_count):
            total = matrix[state].sum()
            if total == 0:
                matrix[state, state] = 1.0
            else:
                matrix[state] = matrix[state] / total
        return pd.DataFrame(matrix, index=range(state_count), columns=range(state_count))

    @staticmethod
    def _safe_div(numerator: float, denominator: Optional[float]) -> Optional[float]:
        if denominator is None or denominator == 0 or pd.isna(denominator):
            return None
        return float(numerator / denominator)

    @staticmethod
    def _normal_pdf(value: float) -> float:
        return math.exp(-(value**2) / 2) / math.sqrt(2 * math.pi)

    @staticmethod
    def _optional_float(value) -> Optional[float]:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _to_date(value) -> date:
        if isinstance(value, date):
            return value
        return pd.Timestamp(value).date()

    @staticmethod
    def _validate_date_range(start_date: Optional[date], end_date: Optional[date]) -> None:
        if start_date is not None and end_date is not None and end_date < start_date:
            raise AppError(
                "end_date must be greater than or equal to start_date.",
                code="INVALID_DATE_RANGE",
                status_code=422,
            )

    @staticmethod
    def _health_score(metrics: dict) -> float:
        score = 100
        score -= min(abs(metrics["max_drawdown"]) * 100, 40)
        score -= min(metrics["annualized_volatility"] * 50, 30)
        if metrics["sharpe"] is not None:
            score += max(min(metrics["sharpe"] * 5, 10), -10)
        return float(max(0, min(100, score)))
