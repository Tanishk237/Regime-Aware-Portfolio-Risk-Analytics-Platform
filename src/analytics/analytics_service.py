from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.analytics.regime_service import AnalyticsRegimeService
from src.analytics.returns_repository import AnalyticsReturnsRepository
from src.analytics.risk_service import AnalyticsRiskService
from src.analytics.utils import AnalyticsUtils
from src.database.models import Portfolio, Trade, User
from src.market import MarketDataService
from src.portfolio.portfolio_service import PortfolioService


class AnalyticsService(
    AnalyticsUtils,
    AnalyticsReturnsRepository,
    AnalyticsRiskService,
    AnalyticsRegimeService,
):
    def __init__(
        self,
        db: Session,
        *,
        market_data_service: Optional[MarketDataService] = None,
        model_dir: str = "models",
        runtime_hmm_fit_enabled: bool = True,
        max_regime_observations: int = 1_500,
        max_history_days: int = 3_650,
    ):
        self.db = db
        self.market_data_service = market_data_service or MarketDataService(db)
        self.model_dir = model_dir
        self.runtime_hmm_fit_enabled = runtime_hmm_fit_enabled
        self.max_regime_observations = max_regime_observations
        self.max_history_days = max_history_days

    def _validate_work_window(self, start_date: date, end_date: Optional[date]) -> None:
        final_date = end_date or date.today()
        if (final_date - start_date).days > self.max_history_days:
            raise AppError(
                "The requested analytics window is too large.",
                code="ANALYTICS_WINDOW_TOO_LARGE",
                status_code=422,
                details={"maximum_days": self.max_history_days},
            )

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
        portfolio_service = PortfolioService(
            self.db,
            market_data_service=self.market_data_service,
        )
        portfolio = portfolio_service.get_portfolio(user, portfolio_id)
        self.market_data_service.allow_demo_data = portfolio.is_demo
        first_trade_date = self._portfolio_first_trade_date(portfolio.id)
        start_date = max(start_date or first_trade_date, first_trade_date)
        self._validate_date_range(start_date, end_date)
        self._validate_work_window(start_date, end_date)
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
        portfolio_service = PortfolioService(
            self.db,
            market_data_service=self.market_data_service,
        )
        portfolio = portfolio_service.get_portfolio(user, portfolio_id)
        self.market_data_service.allow_demo_data = portfolio.is_demo
        first_trade_date = self._portfolio_first_trade_date(portfolio.id)
        start_date = max(start_date or first_trade_date, first_trade_date)
        self._validate_date_range(start_date, end_date)
        self._validate_work_window(start_date, end_date)
        positions = portfolio_service.list_positions(user, portfolio.id)
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
        feature_matrix = feature_matrix.tail(self.max_regime_observations)
        regime_payload = self._predict_regimes(feature_matrix)

        if persist:
            self._persist_regime_predictions(portfolio.id, regime_payload["history"])

        feature_metadata = feature_payload["metadata"]
        feature_metadata["model_name"] = regime_payload["model_name"]
        feature_metadata["model_fallback_used"] = regime_payload["model_fallback_used"]
        feature_metadata["fallback_used"] = bool(
            feature_metadata.get("fallback_used") or regime_payload["model_fallback_used"]
        )
        explanation = self._build_regime_explanation(regime_payload)

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
            "feature_metadata": feature_metadata,
            "explanation": explanation,
        }

    @staticmethod
    def _build_regime_explanation(regime_payload: dict) -> dict:
        current_state = int(regime_payload["current_state"])
        current_label = str(regime_payload["current_regime"])
        statistics = next(
            (
                row
                for row in regime_payload["statistics"]
                if int(row["hidden_state"]) == current_state
            ),
            {},
        )
        durations = regime_payload["duration"]
        current_duration = int(durations[-1]["duration_days"]) if durations else 0
        drivers = []
        for key, label, percent in (
            ("average_return", "Average daily return", True),
            ("average_volatility", "Average 20-day volatility", True),
            ("average_drawdown", "Average drawdown", True),
            ("average_vix", "Average India VIX", False),
        ):
            value = statistics.get(key)
            if value is None:
                continue
            rendered = f"{float(value) * 100:.2f}%" if percent else f"{float(value):.2f}"
            drivers.append(f"{label}: {rendered}")

        transition_rows = regime_payload.get("transition_matrix") or []
        state_labels = regime_payload.get("state_labels") or {}
        likely_state = None
        likely_probability = None
        if current_state < len(transition_rows) and transition_rows[current_state]:
            transition_row = transition_rows[current_state]
            likely_state_id = max(range(len(transition_row)), key=transition_row.__getitem__)
            likely_state = state_labels.get(str(likely_state_id), f"State {likely_state_id}")
            likely_probability = float(transition_row[likely_state_id])

        probability = float(regime_payload["regime_probability"])
        return {
            "summary": (
                f"The latest validated feature observation is most consistent with the "
                f"{current_label} state at {probability * 100:.1f}% state-fit probability."
            ),
            "drivers": drivers,
            "current_duration_days": current_duration,
            "likely_next_state": likely_state,
            "likely_next_probability": likely_probability,
            "model_mode": str(regime_payload["model_name"]),
            "probability_note": (
                "This probability measures how well the latest observation fits the hidden "
                "state. It is not forecast accuracy or a probability of a future market outcome."
            ),
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
        self.include_demo_market_data = portfolio.is_demo
        positions = PortfolioService(
            self.db,
            market_data_service=self.market_data_service,
        ).list_positions(user, portfolio.id)
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

    def _portfolio_first_trade_date(self, portfolio_id: int) -> date:
        first_trade_date = self.db.scalar(
            select(func.min(Trade.transaction_date)).where(
                Trade.portfolio_id == portfolio_id
            )
        )
        if first_trade_date is not None:
            return first_trade_date
        portfolio = self.db.get(Portfolio, portfolio_id)
        return portfolio.created_at.date() if portfolio is not None else date.today()
