from __future__ import annotations

from datetime import date

from sqlalchemy import select

from src.api.errors import AppError
from src.database.models import Trade, User


class PortfolioTradeService:
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
                .order_by(Trade.transaction_date, Trade.id)
            )
        )

    def add_trade(
        self,
        user: User,
        portfolio_id: int,
        *,
        ticker: str,
        transaction_type: str = "BUY",
        quantity: float,
        price: float,
        transaction_date: date,
        broker: str | None = None,
        fees: float = 0.0,
        taxes: float = 0.0,
        currency: str = "INR",
        notes: str | None = None,
    ) -> Trade:
        self.get_portfolio(user, portfolio_id)
        trade = Trade(
            portfolio_id=portfolio_id,
            ticker=ticker.upper().strip(),
            transaction_type=transaction_type.upper().strip(),
            quantity=float(quantity),
            price=float(price),
            transaction_date=transaction_date,
            broker=broker,
            fees=float(fees),
            taxes=float(taxes),
            currency=currency.upper(),
            notes=notes,
        )
        self.db.add(trade)
        try:
            self.db.flush()
            self.recalculate_positions(user, portfolio_id)
            self.db.refresh(trade)
        except Exception:
            self.db.rollback()
            raise

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
            if key in ("transaction_type", "currency"):
                value = value.upper().strip()
            setattr(trade, key, value)

        try:
            self.db.flush()
            self.recalculate_positions(user, portfolio_id)
            self.db.refresh(trade)
        except Exception:
            self.db.rollback()
            raise

        return trade

    def delete_trade(
        self,
        user: User,
        portfolio_id: int,
        trade_id: int,
    ) -> None:
        trade = self.get_trade(user, portfolio_id, trade_id)
        self.db.delete(trade)
        try:
            self.db.flush()
            self.recalculate_positions(user, portfolio_id)
        except Exception:
            self.db.rollback()
            raise
