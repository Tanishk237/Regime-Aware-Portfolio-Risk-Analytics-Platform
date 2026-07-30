from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import StringIO

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.database.models import Portfolio, PortfolioReturn, Position, Trade, User
from src.portfolio.position_engine import PositionEngine


REQUIRED_TRADE_COLUMNS = {
    "ticker",
    "shares",
    "buy_date",
    "buy_price",
}


@dataclass
class TradeLike:
    ticker: str
    shares: float
    buy_date: date
    buy_price: float


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    def list_portfolios(self, user: User) -> list[Portfolio]:
        return list(
            self.db.scalars(
                select(Portfolio)
                .where(Portfolio.user_id == user.id)
                .order_by(Portfolio.created_at.desc(), Portfolio.id.desc())
            )
        )

    def create_portfolio(
        self,
        user: User,
        *,
        name: str,
        description: str | None = None,
        base_currency: str = "INR",
    ) -> Portfolio:
        portfolio = Portfolio(
            user_id=user.id,
            name=name.strip(),
            description=description,
            base_currency=base_currency.upper(),
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)

        return portfolio

    def get_portfolio(
        self,
        user: User,
        portfolio_id: int,
    ) -> Portfolio:
        portfolio = self.db.scalar(
            select(Portfolio).where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user.id,
            )
        )

        if portfolio is None:
            raise AppError(
                "Portfolio not found.",
                code="PORTFOLIO_NOT_FOUND",
                status_code=404,
            )

        return portfolio

    def update_portfolio(
        self,
        user: User,
        portfolio_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        base_currency: str | None = None,
        update_description: bool = False,
    ) -> Portfolio:
        portfolio = self.get_portfolio(user, portfolio_id)

        if name is not None:
            portfolio.name = name.strip()
        if update_description:
            portfolio.description = description
        if base_currency is not None:
            portfolio.base_currency = base_currency.upper()

        self.db.commit()
        self.db.refresh(portfolio)

        return portfolio

    def delete_portfolio(
        self,
        user: User,
        portfolio_id: int,
    ) -> None:
        portfolio = self.get_portfolio(user, portfolio_id)
        self.db.delete(portfolio)
        self.db.commit()

    def list_trades(
        self,
        user: User,
        portfolio_id: int,
    ) -> list[Trade]:
        self.get_portfolio(user, portfolio_id)

        return list(
            self.db.scalars(
                select(Trade)
                .where(Trade.portfolio_id == portfolio_id)
                .order_by(Trade.buy_date, Trade.id)
            )
        )

    def add_trade(
        self,
        user: User,
        portfolio_id: int,
        *,
        ticker: str,
        shares: float,
        buy_date: date,
        buy_price: float,
        notes: str | None = None,
    ) -> Trade:
        self.get_portfolio(user, portfolio_id)
        trade = Trade(
            portfolio_id=portfolio_id,
            ticker=ticker.upper().strip(),
            shares=float(shares),
            buy_date=buy_date,
            buy_price=float(buy_price),
            notes=notes,
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        self.recalculate_positions(user, portfolio_id)

        return trade

    def get_trade(
        self,
        user: User,
        portfolio_id: int,
        trade_id: int,
    ) -> Trade:
        self.get_portfolio(user, portfolio_id)
        trade = self.db.scalar(
            select(Trade).where(
                Trade.id == trade_id,
                Trade.portfolio_id == portfolio_id,
            )
        )

        if trade is None:
            raise AppError(
                "Trade not found.",
                code="TRADE_NOT_FOUND",
                status_code=404,
            )

        return trade

    def update_trade(
        self,
        user: User,
        portfolio_id: int,
        trade_id: int,
        **updates,
    ) -> Trade:
        trade = self.get_trade(user, portfolio_id, trade_id)

        for key, value in updates.items():
            if value is None:
                continue
            if key == "ticker":
                value = value.upper().strip()
            setattr(trade, key, value)

        self.db.commit()
        self.db.refresh(trade)
        self.recalculate_positions(user, portfolio_id)

        return trade

    def delete_trade(
        self,
        user: User,
        portfolio_id: int,
        trade_id: int,
    ) -> None:
        trade = self.get_trade(user, portfolio_id, trade_id)
        self.db.delete(trade)
        self.db.commit()
        self.recalculate_positions(user, portfolio_id)

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

        position_frame = PositionEngine().build_positions(
            [
                TradeLike(
                    ticker=trade.ticker,
                    shares=trade.shares,
                    buy_date=trade.buy_date,
                    buy_price=trade.buy_price,
                )
                for trade in trades
            ]
        )

        total_cost_basis = float(
            (
                position_frame["shares"]
                * position_frame["avg_cost"]
            ).sum()
        )
        positions: list[Position] = []

        for row in position_frame.to_dict(orient="records"):
            cost_basis = float(row["shares"] * row["avg_cost"])
            position = Position(
                portfolio_id=portfolio_id,
                ticker=row["ticker"],
                shares=float(row["shares"]),
                avg_cost=float(row["avg_cost"]),
                cost_basis=cost_basis,
                current_price=None,
                market_value=None,
                market_weight=None,
                cost_weight=cost_basis / total_cost_basis if total_cost_basis else None,
            )
            self.db.add(position)
            positions.append(position)

        self.db.commit()
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

        return positions

    def list_returns(
        self,
        user: User,
        portfolio_id: int,
    ) -> list[PortfolioReturn]:
        self.get_portfolio(user, portfolio_id)

        return list(
            self.db.scalars(
                select(PortfolioReturn)
                .where(PortfolioReturn.portfolio_id == portfolio_id)
                .order_by(PortfolioReturn.date)
            )
        )

    def build_summary(
        self,
        user: User,
        portfolio_id: int,
    ) -> dict:
        portfolio = self.get_portfolio(user, portfolio_id)
        trades = self.list_trades(user, portfolio_id)
        positions = self.list_positions(user, portfolio_id)
        returns = self.list_returns(user, portfolio_id)

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
            "latest_return": returns[-1].return_value if returns else None,
            "total_return": returns[-1].cumulative_return if returns else None,
        }

    def upload_trades_csv(
        self,
        user: User,
        *,
        name: str,
        description: str | None,
        base_currency: str,
        csv_text: str,
    ) -> tuple[Portfolio, list[Trade], list[Position]]:
        try:
            df = pd.read_csv(StringIO(csv_text))
        except Exception as exc:
            raise AppError(
                "Invalid CSV file.",
                code="INVALID_CSV",
                status_code=400,
                details=str(exc),
            ) from exc

        missing_columns = sorted(
            REQUIRED_TRADE_COLUMNS - set(df.columns)
        )
        if missing_columns:
            raise AppError(
                "CSV is missing required columns.",
                code="CSV_MISSING_COLUMNS",
                status_code=400,
                details={"missing_columns": missing_columns},
            )

        portfolio = self.create_portfolio(
            user,
            name=name,
            description=description,
            base_currency=base_currency,
        )
        trades: list[Trade] = []

        try:
            for row in df.to_dict(orient="records"):
                trade = Trade(
                    portfolio_id=portfolio.id,
                    ticker=str(row["ticker"]).upper().strip(),
                    shares=float(row["shares"]),
                    buy_date=pd.to_datetime(row["buy_date"]).date(),
                    buy_price=float(row["buy_price"]),
                    notes=row.get("notes"),
                )
                if trade.shares <= 0 or trade.buy_price <= 0:
                    raise ValueError("shares and buy_price must be positive")
                self.db.add(trade)
                trades.append(trade)

            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            self.db.delete(portfolio)
            self.db.commit()
            raise AppError(
                "CSV contains invalid trade data.",
                code="INVALID_TRADE_CSV",
                status_code=400,
                details=str(exc),
            ) from exc

        for trade in trades:
            self.db.refresh(trade)

        positions = self.recalculate_positions(
            user,
            portfolio.id,
        )
        self.db.refresh(portfolio)

        return portfolio, trades, positions
