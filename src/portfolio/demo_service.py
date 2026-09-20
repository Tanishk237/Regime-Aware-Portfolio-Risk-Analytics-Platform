from __future__ import annotations

import logging
import math
from datetime import date, timedelta

from sqlalchemy import delete, func, select

from src.analytics import AnalyticsService
from src.api.errors import AppError
from src.database.models import (
    MarketPrice,
    Portfolio,
    PortfolioReturn,
    Position,
    Recommendation,
    RegimePrediction,
    RiskMetric,
    StressResult,
    Trade,
    User,
)
from src.market import MarketDataService
from src.market.providers import MarketDataProvider


logger = logging.getLogger(__name__)

DEMO_PORTFOLIO_NAME = "Latent India Equity Demo"
DEMO_START_DAYS = 365
DEMO_HOLDINGS = (
    ("RELIANCE.NS", 72.0, 1320.0),
    ("HDFCBANK.NS", 88.0, 1575.0),
    ("INFY.NS", 62.0, 1450.0),
    ("TCS.NS", 27.0, 3650.0),
    ("ICICIBANK.NS", 145.0, 1165.0),
    ("MARUTI.NS", 14.0, 11050.0),
)


class _StoredDataOnlyProvider(MarketDataProvider):
    """Ensures the demo never waits on an external provider."""

    name = "stored-demo"

    def get_ohlcv(self, tickers, start_date, end_date=None):
        raise RuntimeError("Demo analytics only use bundled market history.")

    def get_live_price(self, ticker, *, include_name=False):
        raise RuntimeError("Demo analytics only use bundled market history.")

    def get_india_vix(self, start_date, end_date=None):
        raise RuntimeError("Demo analytics only use bundled market history.")


class PortfolioDemoService:
    def __init__(
        self,
        db,
        *,
        runtime_hmm_fit_enabled: bool = True,
        max_regime_observations: int = 1_500,
        max_history_days: int = 3_650,
        max_portfolios_per_user: int = 50,
        max_portfolios_per_guest: int = 5,
    ):
        self.db = db
        self.runtime_hmm_fit_enabled = runtime_hmm_fit_enabled
        self.max_regime_observations = max_regime_observations
        self.max_history_days = max_history_days
        self.max_portfolios_per_user = max_portfolios_per_user
        self.max_portfolios_per_guest = max_portfolios_per_guest

    def create_demo_portfolio(
        self,
        user: User,
        *,
        reset: bool = False,
    ) -> tuple[Portfolio, int, bool]:
        existing = self.db.scalar(
            select(Portfolio)
            .where(Portfolio.user_id == user.id, Portfolio.is_demo.is_(True))
            .order_by(Portfolio.created_at.desc())
        )
        if existing is not None and not reset:
            return existing, 0, self._has_precomputed_analytics(existing.id)

        if existing is not None:
            self._delete_demo_portfolio(existing.id)
        else:
            portfolio_count = self.db.scalar(
                select(func.count(Portfolio.id)).where(Portfolio.user_id == user.id)
            ) or 0
            maximum = (
                self.max_portfolios_per_guest
                if user.is_guest
                else self.max_portfolios_per_user
            )
            if portfolio_count >= maximum:
                raise AppError(
                    "Portfolio limit reached. Delete an existing portfolio before creating the demo.",
                    code="PORTFOLIO_LIMIT_REACHED",
                    status_code=409,
                    details={"maximum": maximum},
                )

        start_date = date.today() - timedelta(days=DEMO_START_DAYS)
        self._seed_market_history(start_date)

        portfolio = Portfolio(
            user_id=user.id,
            name=DEMO_PORTFOLIO_NAME,
            description="Sample Indian equity basket generated for product exploration.",
            base_currency="INR",
            benchmark="NIFTY50",
            is_demo=True,
        )
        self.db.add(portfolio)
        self.db.flush()

        for offset, (ticker, quantity, price) in enumerate(DEMO_HOLDINGS):
            self.db.add(
                Trade(
                    portfolio_id=portfolio.id,
                    ticker=ticker,
                    transaction_type="BUY",
                    quantity=quantity,
                    price=price,
                    transaction_date=start_date + timedelta(days=offset),
                    broker="Latent Demo",
                    currency="INR",
                )
            )
        self.db.commit()
        self.db.refresh(portfolio)

        from src.portfolio.portfolio_service import PortfolioService

        PortfolioService(
            self.db,
            market_data_service=MarketDataService(
                self.db,
                provider=_StoredDataOnlyProvider(),
                allow_demo_data=True,
            ),
        ).recalculate_positions(user, portfolio.id)
        analytics_precomputed = self._precompute_analytics(user, portfolio.id, start_date)
        self._seed_recommendations(portfolio.id)

        return portfolio, len(DEMO_HOLDINGS), analytics_precomputed

    def _seed_market_history(self, start_date: date) -> None:
        end_date = date.today()
        tickers = [ticker for ticker, _, _ in DEMO_HOLDINGS]
        existing = set(
            self.db.execute(
                select(MarketPrice.ticker, MarketPrice.date).where(
                    MarketPrice.ticker.in_(tickers),
                    MarketPrice.date >= start_date,
                    MarketPrice.date <= end_date,
                )
            ).all()
        )

        for ticker_index, (ticker, _, purchase_price) in enumerate(DEMO_HOLDINGS):
            for day_index in range((end_date - start_date).days + 1):
                row_date = start_date + timedelta(days=day_index)
                if (ticker, row_date) in existing:
                    continue
                close = self._demo_close(purchase_price, day_index, ticker_index)
                self.db.add(
                    MarketPrice(
                        ticker=ticker,
                        date=row_date,
                        open=close * 0.996,
                        high=close * 1.008,
                        low=close * 0.992,
                        close=close,
                        volume=1_000_000 + ticker_index * 75_000 + day_index * 500,
                        data_source="demo",
                    )
                )
        self.db.commit()

    @staticmethod
    def _demo_close(base_price: float, day_index: int, ticker_index: int) -> float:
        trend = 1 - 0.00016 * day_index
        cycle = 1 + 0.028 * math.sin(day_index / 13 + ticker_index * 0.8)
        stress = 1 - 0.085 * math.exp(-((day_index - 205) / 34) ** 2)
        recovery = 1 + max(0, day_index - 255) * 0.00022
        return round(max(base_price * 0.65, base_price * trend * cycle * stress * recovery), 2)

    def _precompute_analytics(self, user: User, portfolio_id: int, start_date: date) -> bool:
        try:
            market_service = MarketDataService(self.db, provider=_StoredDataOnlyProvider())
            analytics = AnalyticsService(
                self.db,
                market_data_service=market_service,
                runtime_hmm_fit_enabled=self.runtime_hmm_fit_enabled,
                max_regime_observations=self.max_regime_observations,
                max_history_days=self.max_history_days,
            )
            analytics.build_risk_payload(
                user,
                portfolio_id,
                start_date=start_date,
                end_date=date.today(),
                persist=True,
            )
            analytics.build_regime_payload(
                user,
                portfolio_id,
                start_date=start_date,
                end_date=date.today(),
                persist=True,
            )
            return True
        except Exception as exc:
            logger.warning("Demo portfolio analytics could not be precomputed: %s", exc)
            return False

    def _seed_recommendations(self, portfolio_id: int) -> None:
        self.db.execute(delete(Recommendation).where(Recommendation.portfolio_id == portfolio_id))
        today = date.today()
        self.db.add_all(
            [
                Recommendation(
                    portfolio_id=portfolio_id,
                    date=today,
                    severity="MEDIUM",
                    category="Diversification",
                    title="Review concentration before adding exposure",
                    description="Use the position table and portfolio-health view to check the largest holdings.",
                ),
                Recommendation(
                    portfolio_id=portfolio_id,
                    date=today,
                    severity="LOW",
                    category="Regime",
                    title="Use the regime signal with risk context",
                    description="The demo is for exploration; review confidence, drawdown, and VaR together before acting.",
                ),
            ]
        )
        self.db.commit()

    def _delete_demo_portfolio(self, portfolio_id: int) -> None:
        for model in (
            Recommendation,
            RegimePrediction,
            RiskMetric,
            PortfolioReturn,
            StressResult,
            Position,
            Trade,
        ):
            self.db.execute(delete(model).where(model.portfolio_id == portfolio_id))
        self.db.execute(delete(Portfolio).where(Portfolio.id == portfolio_id))
        self.db.commit()

    def _has_precomputed_analytics(self, portfolio_id: int) -> bool:
        return (
            self.db.scalar(select(RiskMetric.id).where(RiskMetric.portfolio_id == portfolio_id))
            is not None
            and self.db.scalar(select(RegimePrediction.id).where(RegimePrediction.portfolio_id == portfolio_id))
            is not None
        )
