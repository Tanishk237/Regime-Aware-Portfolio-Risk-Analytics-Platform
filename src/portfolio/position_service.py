from __future__ import annotations

from datetime import date

from sqlalchemy import delete, func, select

from src.api.errors import AppError
from src.database.models import MarketPrice, Portfolio, PortfolioReturn, Position, Trade, User


class PortfolioPositionService:
    def recalculate_positions(
        self,
        user: User,
        portfolio_id: int,
    ) -> list[Position]:
        self.get_portfolio(user, portfolio_id)
        trades = self.list_trades(user, portfolio_id)

        self.db.execute(
            delete(Position).where(
                Position.portfolio_id == portfolio_id
            )
        )

        if not trades:
            self.db.commit()
            return []

        position_rows = self._build_position_rows(trades)
        total_cost_basis = sum(row["cost_basis"] for row in position_rows)
        positions: list[Position] = []

        for row in position_rows:
            position = Position(
                portfolio_id=portfolio_id,
                ticker=row["ticker"],
                quantity=float(row["quantity"]),
                avg_cost=float(row["avg_cost"]),
                cost_basis=float(row["cost_basis"]),
                current_price=None,
                market_value=None,
                market_weight=None,
                cost_weight=row["cost_basis"] / total_cost_basis if total_cost_basis else None,
                unrealized_pnl=0.0,
                realized_pnl=float(row["realized_pnl"]),
            )
            self.db.add(position)
            positions.append(position)

        self.db.commit()
        for position in positions:
            self.db.refresh(position)

        self._refresh_position_market_values(portfolio_id)
        for position in positions:
            self.db.refresh(position)

        return positions

    def list_positions(
        self,
        user: User,
        portfolio_id: int,
    ) -> list[Position]:
        self.get_portfolio(user, portfolio_id)
        positions = list(
            self.db.scalars(
                select(Position)
                .where(Position.portfolio_id == portfolio_id)
                .order_by(Position.ticker)
            )
        )

        if not positions:
            positions = self.recalculate_positions(
                user,
                portfolio_id,
            )
        else:
            self._refresh_position_market_values(portfolio_id)
            positions = list(
                self.db.scalars(
                    select(Position)
                    .where(Position.portfolio_id == portfolio_id)
                    .order_by(Position.ticker)
                )
            )

        return positions

    def list_returns(
        self,
        user: User,
        portfolio_id: int,
    ) -> list[PortfolioReturn]:
        portfolio = self.get_portfolio(user, portfolio_id)
        returns = self._stored_returns(portfolio_id)
        if returns:
            return returns

        self._build_missing_returns(user, portfolio)
        return self._stored_returns(portfolio_id)

    def _stored_returns(self, portfolio_id: int) -> list[PortfolioReturn]:
        return list(
            self.db.scalars(
                select(PortfolioReturn)
                .where(PortfolioReturn.portfolio_id == portfolio_id)
                .order_by(PortfolioReturn.date)
            )
        )

    def _build_missing_returns(self, user: User, portfolio: Portfolio) -> None:
        from src.analytics import AnalyticsService

        first_trade_date = self.db.scalar(
            select(func.min(Trade.transaction_date)).where(
                Trade.portfolio_id == portfolio.id
            )
        )
        tickers = list(
            self.db.scalars(
                select(Trade.ticker)
                .where(Trade.portfolio_id == portfolio.id)
                .distinct()
            )
        )
        latest_price_date = (
            self.db.scalar(
                select(func.max(MarketPrice.date)).where(
                    MarketPrice.ticker.in_(tickers)
                )
            )
            if tickers
            else None
        )
        start_date = first_trade_date or portfolio.created_at.date()
        end_date = latest_price_date or date.today()
        AnalyticsService(self.db).build_risk_payload(
            user,
            portfolio.id,
            start_date=start_date,
            end_date=end_date,
            persist=True,
        )

    def build_summary(
        self,
        user: User,
        portfolio_id: int,
    ) -> dict:
        portfolio = self.get_portfolio(user, portfolio_id)
        trades = self.list_trades(user, portfolio_id)
        positions = self.list_positions(user, portfolio_id)
        returns = self._stored_returns(portfolio_id)

        invested_value = sum(
            position.cost_basis
            for position in positions
        )
        market_values = [
            position.market_value
            for position in positions
            if position.market_value is not None
        ]
        current_value = sum(market_values) if market_values else None
        unrealized_profit = (
            current_value - invested_value
            if current_value is not None
            else None
        )
        unrealized_profit_pct = (
            unrealized_profit / invested_value * 100
            if unrealized_profit is not None and invested_value
            else None
        )

        return {
            "portfolio_id": portfolio.id,
            "name": portfolio.name,
            "base_currency": portfolio.base_currency,
            "trades_count": len(trades),
            "positions_count": len(positions),
            "invested_value": invested_value,
            "current_value": current_value,
            "unrealized_profit": unrealized_profit,
            "unrealized_profit_pct": unrealized_profit_pct,
            "realized_profit": sum(position.realized_pnl for position in positions),
            "latest_return": returns[-1].daily_return if returns else None,
            "total_return": returns[-1].cumulative_return if returns else None,
        }

    @staticmethod
    def _build_position_rows(trades: list[Trade]) -> list[dict]:
        holdings: dict[str, dict] = {}

        for trade in sorted(trades, key=lambda item: (item.transaction_date, item.id or 0)):
            ticker = trade.ticker
            holding = holdings.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "quantity": 0.0,
                    "total_cost": 0.0,
                    "realized_pnl": 0.0,
                },
            )
            transaction_costs = float(trade.fees + trade.taxes)

            if trade.transaction_type == "BUY":
                holding["quantity"] += float(trade.quantity)
                holding["total_cost"] += float(
                    trade.quantity * trade.price + transaction_costs
                )
                continue

            if trade.transaction_type != "SELL":
                raise AppError(
                    "Invalid transaction type.",
                    code="INVALID_TRANSACTION_TYPE",
                    status_code=400,
                    details={"transaction_type": trade.transaction_type},
                )

            if trade.quantity > holding["quantity"]:
                raise AppError(
                    "Sell quantity exceeds current holding.",
                    code="INSUFFICIENT_POSITION_QUANTITY",
                    status_code=400,
                    details={
                        "ticker": ticker,
                        "available_quantity": holding["quantity"],
                        "sell_quantity": trade.quantity,
                    },
                )

            avg_cost = (
                holding["total_cost"] / holding["quantity"]
                if holding["quantity"]
                else 0.0
            )
            realized = (
                trade.quantity * trade.price
                - trade.quantity * avg_cost
                - transaction_costs
            )
            holding["realized_pnl"] += float(realized)
            holding["quantity"] -= float(trade.quantity)
            holding["total_cost"] -= float(avg_cost * trade.quantity)

        rows = []
        for holding in holdings.values():
            quantity = float(holding["quantity"])
            avg_cost = (
                float(holding["total_cost"]) / quantity
                if quantity
                else 0.0
            )
            rows.append(
                {
                    "ticker": holding["ticker"],
                    "quantity": quantity,
                    "avg_cost": avg_cost,
                    "cost_basis": float(holding["total_cost"]),
                    "realized_pnl": float(holding["realized_pnl"]),
                }
            )

        return rows
