from __future__ import annotations

from io import StringIO

import pandas as pd

from src.api.errors import AppError
from src.database.models import Portfolio, Position, Trade, User


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


class PortfolioCsvImportService:
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
