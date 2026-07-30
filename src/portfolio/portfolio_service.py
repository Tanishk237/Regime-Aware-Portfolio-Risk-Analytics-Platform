from __future__ import annotations

from datetime import date
from io import StringIO

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.database.models import Portfolio, PortfolioReturn, Position, Trade, User


REQUIRED_TRADE_COLUMNS = {
    "ticker",
    "quantity",
    "transaction_date",
    "price",
}

LEGACY_TRADE_COLUMN_MAP = {
    "shares": "quantity",
    "buy_date": "transaction_date",
    "buy_price": "price",
}


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
        benchmark: str = "NIFTY50",
    ) -> Portfolio:
        portfolio = Portfolio(
            user_id=user.id,
            name=name.strip(),
            description=description,
            base_currency=base_currency.upper(),
            benchmark=benchmark.upper(),
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
        benchmark: str | None = None,
        update_description: bool = False,
    ) -> Portfolio:
        portfolio = self.get_portfolio(user, portfolio_id)

        if name is not None:
            portfolio.name = name.strip()
        if update_description:
            portfolio.description = description
        if base_currency is not None:
            portfolio.base_currency = base_currency.upper()
        if benchmark is not None:
            portfolio.benchmark = benchmark.upper()

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
            "realized_profit": sum(position.realized_pnl for position in positions),
            "latest_return": returns[-1].daily_return if returns else None,
            "total_return": returns[-1].cumulative_return if returns else None,
        }

    def upload_trades_csv(
        self,
        user: User,
        *,
        name: str,
        description: str | None,
        base_currency: str,
        benchmark: str = "NIFTY50",
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

        df = self._normalize_trade_csv_columns(df)

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
            benchmark=benchmark,
        )
        trades: list[Trade] = []

        try:
            for row in df.to_dict(orient="records"):
                trade = Trade(
                    portfolio_id=portfolio.id,
                    ticker=str(row["ticker"]).upper().strip(),
                    transaction_type=str(row.get("transaction_type", "BUY")).upper().strip(),
                    quantity=float(row["quantity"]),
                    price=float(row["price"]),
                    transaction_date=pd.to_datetime(row["transaction_date"]).date(),
                    broker=row.get("broker"),
                    fees=float(row.get("fees", 0.0) or 0.0),
                    taxes=float(row.get("taxes", 0.0) or 0.0),
                    currency=str(row.get("currency", portfolio.base_currency)).upper().strip(),
                    notes=row.get("notes"),
                )
                if trade.transaction_type not in ("BUY", "SELL"):
                    raise ValueError("transaction_type must be BUY or SELL")
                if trade.quantity <= 0 or trade.price <= 0:
                    raise ValueError("quantity and price must be positive")
                if trade.fees < 0 or trade.taxes < 0:
                    raise ValueError("fees and taxes must be non-negative")
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

    @staticmethod
    def _normalize_trade_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for old_column, new_column in LEGACY_TRADE_COLUMN_MAP.items():
            if old_column in df.columns and new_column not in df.columns:
                df[new_column] = df[old_column]

        if "transaction_type" not in df.columns:
            df["transaction_type"] = "BUY"

        return df

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
