from __future__ import annotations

import logging
from datetime import date
from typing import Iterable, Optional

import pandas as pd
from fastapi import status

from src.api.errors import AppError


logger = logging.getLogger(__name__)


class MarketDataUtils:
    @staticmethod
    def _normalize_tickers(tickers: Iterable[str]) -> list[str]:
        normalized = [MarketDataUtils._normalize_symbol(ticker) for ticker in tickers if ticker and ticker.strip()]
        if not normalized:
            raise AppError(
                "At least one ticker is required.",
                code="TICKERS_REQUIRED",
                status_code=422,
            )
        return normalized

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        ticker = symbol.strip().upper()
        if ticker.startswith("^") or "." in ticker:
            return ticker
        return f"{ticker}.NS"

    @staticmethod
    def _normalize_weights(weights: list[float]) -> list[float]:
        total = sum(weights)
        if total <= 0:
            raise AppError(
                "Weights must sum to a positive value.",
                code="INVALID_WEIGHTS",
                status_code=422,
            )
        return [weight / total for weight in weights]

    @staticmethod
    def _ensure_dataframe(prices: pd.DataFrame | pd.Series, tickers: list[str]) -> pd.DataFrame:
        if isinstance(prices, pd.Series):
            return prices.to_frame(name=tickers[0])
        prices = prices.copy()
        if not isinstance(prices.columns, pd.MultiIndex):
            if len(tickers) == 1 and len(prices.columns) == 1:
                prices.columns = [tickers[0]]
            return prices
        if "Close" in prices.columns.get_level_values(0):
            prices = prices["Close"]
        return prices

    @staticmethod
    def _filter_date_range(
        frame: pd.DataFrame,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> pd.DataFrame:
        filtered = frame.copy()
        if start_date is not None:
            filtered = filtered[filtered.index.date >= start_date]
        if end_date is not None:
            filtered = filtered[filtered.index.date <= end_date]
        return filtered

    @staticmethod
    def _cache_key(
        namespace: str,
        tickers: list[str],
        start_date: Optional[date],
        end_date: Optional[date],
        *parts,
    ) -> str:
        tickers_key = ",".join(sorted(tickers))
        return ":".join(
            [
                namespace,
                tickers_key,
                str(start_date or ""),
                str(end_date or ""),
                *[str(part) for part in parts],
            ]
        )

    @staticmethod
    def _validate_date_range(
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> None:
        if start_date is not None and end_date is not None and end_date < start_date:
            raise AppError(
                "end_date must be greater than or equal to start_date.",
                code="INVALID_DATE_RANGE",
                status_code=422,
            )

    @staticmethod
    def _to_date(value) -> date:
        if isinstance(value, date):
            return value
        return pd.Timestamp(value).date()

    @staticmethod
    def _optional_float(value) -> Optional[float]:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _json_ready(value):
        if isinstance(value, dict):
            return {key: MarketDataUtils._json_ready(item) for key, item in value.items()}
        if isinstance(value, list):
            return [MarketDataUtils._json_ready(item) for item in value]
        if hasattr(value, "item"):
            return value.item()
        return value

    @staticmethod
    def _market_data_error(message: str, exc: Exception) -> AppError:
        logger.warning("%s %s", message, exc)
        return AppError(
            message,
            code="MARKET_DATA_UNAVAILABLE",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"error": str(exc)},
        )
