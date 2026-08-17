from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.analytics.regime_service import AnalyticsRegimeService
from src.analytics.returns_repository import AnalyticsReturnsRepository
from src.analytics.risk_service import AnalyticsRiskService
from src.analytics.utils import AnalyticsUtils
from src.database.models import Portfolio, User
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
