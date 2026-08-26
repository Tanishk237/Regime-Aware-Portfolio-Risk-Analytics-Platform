from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import func, select

from src.api.errors import AppError
from src.database.models import MarketPrice, Position, Trade
from src.market import MarketDataService


logger = logging.getLogger(__name__)


class PortfolioMarketValuationService:
    def _refresh_position_market_values(self, portfolio_id: int) -> None:
        positions = list(
            self.db.scalars(
                select(Position)
                .where(Position.portfolio_id == portfolio_id)
                .order_by(Position.ticker)
            )
        )
        open_positions = [position for position in positions if position.quantity > 0]
        if not open_positions:
            return

        tickers = [position.ticker for position in open_positions]
        start_date = self._portfolio_first_trade_date(portfolio_id)
        if start_date is not None:
            self._backfill_market_prices(tickers, start_date)

        latest_prices = self._latest_prices_by_ticker(tickers)
        total_market_value = 0.0
        valued_positions = []

        for position in open_positions:
            current_price = latest_prices.get(position.ticker)
            if current_price is None:
                continue
            position.current_price = current_price
            position.market_value = float(position.quantity) * current_price
            position.unrealized_pnl = position.market_value - float(position.cost_basis)
            total_market_value += position.market_value
            valued_positions.append(position)

        if total_market_value:
            for position in valued_positions:
                position.market_weight = float(position.market_value) / total_market_value

        self.db.commit()

    def _backfill_market_prices(self, tickers: list[str], start_date: date) -> None:
        try:
            MarketDataService(self.db).get_historical_prices(
                tickers,
                start_date,
                date.today(),
                persist=True,
            )
        except AppError as exc:
            logger.warning(
                "Could not refresh market prices for portfolio valuation: %s",
                exc.message,
            )
        except Exception as exc:
            logger.warning(
                "Unexpected market price refresh failure for portfolio valuation: %s",
                exc,
            )

    def _portfolio_first_trade_date(self, portfolio_id: int) -> date | None:
        return self.db.scalar(
            select(func.min(Trade.transaction_date)).where(
                Trade.portfolio_id == portfolio_id
            )
        )

    def _latest_prices_by_ticker(self, tickers: list[str]) -> dict[str, float]:
        latest_prices: dict[str, float] = {}
        for ticker in tickers:
            row = (
                self.db.query(MarketPrice)
                .filter(MarketPrice.ticker == ticker)
                .order_by(MarketPrice.date.desc())
                .first()
            )
            if row is not None:
                latest_prices[ticker] = float(row.close)
        return latest_prices
