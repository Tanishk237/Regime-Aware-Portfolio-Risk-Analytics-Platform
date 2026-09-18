from __future__ import annotations

from io import StringIO
import re
from typing import Any

import pandas as pd

from src.api.errors import AppError
from src.database.models import Portfolio, Position, Trade, User


REQUIRED_TRADE_COLUMNS = {"ticker", "quantity", "transaction_date", "price"}
TRADE_COLUMNS = {
    *REQUIRED_TRADE_COLUMNS,
    "transaction_type",
    "broker",
    "fees",
    "taxes",
    "currency",
    "notes",
}
TRADE_COLUMN_ALIASES = {
    "symbol": "ticker",
    "stock": "ticker",
    "security": "ticker",
    "instrument": "ticker",
    "ticker_symbol": "ticker",
    "shares": "quantity",
    "qty": "quantity",
    "units": "quantity",
    "buy_date": "transaction_date",
    "trade_date": "transaction_date",
    "order_date": "transaction_date",
    "date": "transaction_date",
    "buy_price": "price",
    "trade_price": "price",
    "execution_price": "price",
    "rate": "price",
    "type": "transaction_type",
    "side": "transaction_type",
    "action": "transaction_type",
    "trade_type": "transaction_type",
    "brokerage": "fees",
    "charges": "fees",
    "tax": "taxes",
    "remarks": "notes",
}

TRANSACTION_TYPE_ALIASES = {
    "B": "BUY",
    "BOT": "BUY",
    "PURCHASE": "BUY",
    "S": "SELL",
    "SLD": "SELL",
    "SALE": "SELL",
}


class PortfolioCsvImportService:
    def preview_trades_csv(self, csv_text: str) -> dict[str, Any]:
        _, report = self._parse_and_validate_trade_csv(csv_text)
        return report

    def resolve_trades_csv(self, csv_text: str) -> dict[str, Any]:
        """Apply deterministic CSV repairs and return a freshly validated file."""
        raw = self._read_csv(csv_text)
        frame, _, column_mapping, _ = self._normalize_columns(raw)
        changes: list[dict[str, Any]] = []

        for original, normalized in column_mapping.items():
            changes.append(
                self._change(None, normalized, original, normalized, "Mapped a recognized column name.")
            )

        defaults = {
            "transaction_type": "BUY",
            "currency": "INR",
            "fees": 0.0,
            "taxes": 0.0,
        }
        for field, value in defaults.items():
            if field not in frame.columns:
                frame[field] = value
                changes.append(
                    self._change(None, field, None, value, f"Added the default {field} value.")
                )

        for index in frame.index:
            row_number = int(index) + 2
            if "ticker" in frame.columns:
                self._repair_cell(
                    frame,
                    index,
                    row_number,
                    "ticker",
                    self._repair_ticker,
                    "Normalized the ticker symbol.",
                    changes,
                )
            if "transaction_type" in frame.columns:
                self._repair_cell(
                    frame,
                    index,
                    row_number,
                    "transaction_type",
                    self._repair_transaction_type,
                    "Normalized the trade action.",
                    changes,
                )
            for field in ("quantity", "price", "fees", "taxes"):
                if field in frame.columns:
                    self._repair_cell(
                        frame,
                        index,
                        row_number,
                        field,
                        self._repair_number,
                        "Removed currency and thousands formatting.",
                        changes,
                    )
            if "transaction_date" in frame.columns:
                self._repair_cell(
                    frame,
                    index,
                    row_number,
                    "transaction_date",
                    self._repair_date,
                    "Converted the date to YYYY-MM-DD.",
                    changes,
                )
            if "currency" in frame.columns:
                self._repair_cell(
                    frame,
                    index,
                    row_number,
                    "currency",
                    self._repair_currency,
                    "Normalized the currency code.",
                    changes,
                )

        resolved_csv = frame.to_csv(index=False, lineterminator="\n")
        _, report = self._parse_and_validate_trade_csv(resolved_csv)
        return {
            "resolved_csv": resolved_csv,
            "changes": changes,
            "report": report,
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
        df, report = self._parse_and_validate_trade_csv(csv_text)
        if not report["valid"]:
            error_code = (
                "CSV_MISSING_COLUMNS"
                if report["missing_columns"]
                else "INVALID_TRADE_CSV"
            )
            raise AppError(
                "CSV contains invalid trade data.",
                code=error_code,
                status_code=400,
                details=report,
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
                    broker=self._optional_text(row.get("broker")),
                    fees=float(row.get("fees", 0.0) or 0.0),
                    taxes=float(row.get("taxes", 0.0) or 0.0),
                    currency=str(row.get("currency", portfolio.base_currency)).upper().strip(),
                    notes=self._optional_text(row.get("notes")),
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

    def _parse_and_validate_trade_csv(
        self,
        csv_text: str,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        raw = self._read_csv(csv_text)
        frame, detected_columns, column_mapping, duplicate_targets = self._normalize_columns(raw)
        if "transaction_type" not in frame.columns:
            frame["transaction_type"] = "BUY"
            column_mapping["(default)"] = "transaction_type"
        if "currency" not in frame.columns:
            frame["currency"] = "INR"
        for column in ("fees", "taxes"):
            if column not in frame.columns:
                frame[column] = 0.0

        missing_columns = sorted(REQUIRED_TRADE_COLUMNS - set(frame.columns))
        unknown_columns = sorted(set(frame.columns) - TRADE_COLUMNS)
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        if duplicate_targets:
            errors.append(
                {
                    "message": "Multiple CSV columns map to the same trade field: "
                    + ", ".join(sorted(duplicate_targets))
                }
            )
        if unknown_columns:
            warnings.append(
                {
                    "message": "Unrecognized columns will be ignored: "
                    + ", ".join(unknown_columns)
                }
            )
        if missing_columns:
            errors.append(
                {
                    "message": "Missing required columns: " + ", ".join(missing_columns)
                }
            )

        if not missing_columns:
            errors.extend(self._normalize_and_validate_rows(frame))

        duplicate_columns = [
            column
            for column in (
                "ticker",
                "transaction_type",
                "quantity",
                "price",
                "transaction_date",
                "fees",
                "taxes",
            )
            if column in frame.columns
        ]
        duplicate_rows = int(frame.duplicated(subset=duplicate_columns, keep=False).sum())
        if duplicate_rows:
            warnings.append(
                {
                    "message": f"{duplicate_rows} rows look identical. Confirm they are separate fills before importing."
                }
            )

        valid_row_numbers = {
            issue["row"] for issue in errors if issue.get("row") is not None
        }
        preview_columns = [column for column in frame.columns if column in TRADE_COLUMNS]
        preview = []
        for row in frame[preview_columns].head(10).to_dict(orient="records"):
            preview.append(
                {
                    key: self._json_value(value)
                    for key, value in row.items()
                }
            )

        report = {
            "valid": not errors,
            "total_rows": int(len(frame)),
            "valid_rows": max(int(len(frame)) - len(valid_row_numbers), 0),
            "duplicate_rows": duplicate_rows,
            "detected_columns": detected_columns,
            "normalized_columns": preview_columns,
            "column_mapping": column_mapping,
            "missing_columns": missing_columns,
            "unknown_columns": unknown_columns,
            "warnings": warnings,
            "errors": errors[:50],
            "preview": preview,
        }
        return frame[preview_columns], report

    def _normalize_and_validate_rows(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
        frame["transaction_type"] = (
            frame["transaction_type"].fillna("BUY").astype(str).str.upper().str.strip()
        )
        frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
        frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
        frame["transaction_date"] = pd.to_datetime(
            frame["transaction_date"], errors="coerce", format="mixed"
        )
        frame["fees"] = pd.to_numeric(frame["fees"], errors="coerce").fillna(0.0)
        frame["taxes"] = pd.to_numeric(frame["taxes"], errors="coerce").fillna(0.0)
        frame["currency"] = frame["currency"].fillna("INR").astype(str).str.upper().str.strip()

        holdings: dict[str, float] = {}
        for row_number, (_, row) in enumerate(frame.iterrows(), start=2):
            ticker = str(row["ticker"])
            transaction_type = str(row["transaction_type"])
            quantity = row["quantity"]
            price = row["price"]
            transaction_date = row["transaction_date"]
            if (
                not ticker
                or ticker in {"NAN", "NONE"}
                or not re.fullmatch(r"[A-Z0-9][A-Z0-9.^_&=-]{0,63}", ticker)
            ):
                errors.append(self._issue(row_number, "ticker", "Enter a valid ticker symbol."))
            if transaction_type not in {"BUY", "SELL"}:
                errors.append(self._issue(row_number, "transaction_type", "Use BUY or SELL."))
            if pd.isna(quantity) or float(quantity) <= 0:
                errors.append(self._issue(row_number, "quantity", "Quantity must be greater than zero."))
            if pd.isna(price) or float(price) <= 0:
                errors.append(self._issue(row_number, "price", "Price must be greater than zero."))
            if pd.isna(transaction_date):
                errors.append(self._issue(row_number, "transaction_date", "Enter a valid trade date."))
            if float(row["fees"]) < 0:
                errors.append(self._issue(row_number, "fees", "Fees cannot be negative."))
            if float(row["taxes"]) < 0:
                errors.append(self._issue(row_number, "taxes", "Taxes cannot be negative."))
            if not re.fullmatch(r"[A-Z]{3,12}", str(row["currency"])):
                errors.append(
                    self._issue(
                        row_number,
                        "currency",
                        "Currency must contain 3 to 12 letters.",
                    )
                )

            if (
                ticker not in {"", "NAN", "NONE"}
                and transaction_type in {"BUY", "SELL"}
                and not pd.isna(quantity)
                and float(quantity) > 0
            ):
                current = holdings.get(ticker, 0.0)
                next_quantity = current + float(quantity) * (1 if transaction_type == "BUY" else -1)
                if next_quantity < -1e-9:
                    errors.append(
                        self._issue(
                            row_number,
                            "quantity",
                            f"SELL exceeds the imported running quantity for {ticker}.",
                        )
                    )
                else:
                    holdings[ticker] = next_quantity

        return errors

    @staticmethod
    def _read_csv(csv_text: str) -> pd.DataFrame:
        try:
            raw = pd.read_csv(StringIO(csv_text))
        except Exception as exc:
            raise AppError(
                "Invalid CSV file.",
                code="INVALID_CSV",
                status_code=400,
                details=str(exc),
            ) from exc

        if raw.empty:
            raise AppError(
                "CSV file has no trade rows.",
                code="CSV_EMPTY",
                status_code=400,
            )
        return raw

    def _normalize_columns(
        self,
        raw: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[str], dict[str, str], set[str]]:
        detected_columns = [str(column) for column in raw.columns]
        normalized_names = [self._column_key(column) for column in raw.columns]
        column_mapping: dict[str, str] = {}
        final_names: list[str] = []
        duplicate_targets: set[str] = set()
        for original, normalized in zip(detected_columns, normalized_names):
            target = TRADE_COLUMN_ALIASES.get(normalized, normalized)
            if target in final_names:
                duplicate_targets.add(target)
                target = normalized
            final_names.append(target)
            if original != target:
                column_mapping[original] = target

        frame = raw.copy()
        frame.columns = final_names
        return frame, detected_columns, column_mapping, duplicate_targets

    def _repair_cell(
        self,
        frame: pd.DataFrame,
        index: Any,
        row_number: int,
        field: str,
        repair: Any,
        reason: str,
        changes: list[dict[str, Any]],
    ) -> None:
        before = frame.at[index, field]
        after = repair(before)
        if self._comparable_value(before) == self._comparable_value(after):
            return
        frame.at[index, field] = after
        changes.append(self._change(row_number, field, before, after, reason))

    @staticmethod
    def _repair_ticker(value: Any) -> Any:
        if value is None or pd.isna(value):
            return value
        ticker = re.sub(r"\s+", "", str(value)).upper()
        if ticker.startswith("NSE:"):
            ticker = f"{ticker[4:]}.NS"
        elif ticker.endswith(".NSE"):
            ticker = f"{ticker[:-4]}.NS"
        return ticker

    @staticmethod
    def _repair_transaction_type(value: Any) -> Any:
        if value is None or pd.isna(value):
            return "BUY"
        action = str(value).strip().upper()
        return TRANSACTION_TYPE_ALIASES.get(action, action)

    @staticmethod
    def _repair_number(value: Any) -> Any:
        if value is None or pd.isna(value) or isinstance(value, (int, float)):
            return value
        normalized = re.sub(r"(?i)\bINR\b", "", str(value))
        normalized = normalized.replace("₹", "").replace(",", "").strip()
        try:
            return float(normalized)
        except ValueError:
            return value

    @staticmethod
    def _repair_date(value: Any) -> Any:
        if value is None or pd.isna(value):
            return value
        text = str(value).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return text
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
        return parsed.date().isoformat() if not pd.isna(parsed) else value

    @staticmethod
    def _repair_currency(value: Any) -> Any:
        if value is None or pd.isna(value) or not str(value).strip():
            return "INR"
        return str(value).strip().upper()

    @classmethod
    def _change(
        cls,
        row: int | None,
        field: str,
        before: Any,
        after: Any,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "row": row,
            "field": field,
            "before": cls._json_value(before),
            "after": cls._json_value(after),
            "reason": reason,
        }

    @staticmethod
    def _comparable_value(value: Any) -> str:
        if value is None or pd.isna(value):
            return ""
        return str(value).strip()

    @staticmethod
    def _column_key(value: Any) -> str:
        return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())).strip("_")

    @staticmethod
    def _issue(row: int | None, field: str, message: str) -> dict[str, Any]:
        return {"row": row, "field": field, "message": message}

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None or pd.isna(value):
            return None
        clean = str(value).strip()
        return clean or None

    @staticmethod
    def _json_value(value: Any) -> Any:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.date().isoformat()
        if hasattr(value, "item"):
            return value.item()
        return value
