from __future__ import annotations

import pandas as pd
from fastapi import status

from src.api.errors import AppError


class MarketDataNormalizers:
    def _normalize_ohlcv(
        self,
        raw_prices: pd.DataFrame,
        tickers: list[str],
    ) -> list[dict]:
        if raw_prices.empty:
            return []

        records = []
        for ticker in tickers:
            frame = self._extract_ticker_ohlcv(raw_prices, ticker, len(tickers) == 1)
            if frame.empty or "Close" not in frame.columns:
                continue

            for row_date, row in frame.dropna(subset=["Close"]).iterrows():
                records.append(
                    {
                        "ticker": ticker,
                        "date": self._to_date(row_date),
                        "open": self._optional_float(row.get("Open")),
                        "high": self._optional_float(row.get("High")),
                        "low": self._optional_float(row.get("Low")),
                        "close": float(row["Close"]),
                        "volume": self._optional_float(row.get("Volume")),
                    }
                )

        return records

    def _normalize_vix_records(
        self,
        vix: pd.DataFrame,
        window: int,
    ) -> list[dict]:
        if "vix" not in vix.columns:
            raise AppError(
                "India VIX data did not contain a vix column.",
                code="MARKET_DATA_INVALID",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        change_column = f"vix_change_{window}"
        records = []
        for row_date, row in vix.dropna(subset=["vix"]).iterrows():
            records.append(
                {
                    "date": self._to_date(row_date),
                    "vix": float(row["vix"]),
                    "vix_change": self._optional_float(row.get(change_column)),
                }
            )
        return records

    @staticmethod
    def _extract_ticker_ohlcv(
        raw_prices: pd.DataFrame,
        ticker: str,
        single_ticker: bool,
    ) -> pd.DataFrame:
        if not isinstance(raw_prices.columns, pd.MultiIndex):
            return raw_prices.copy() if single_ticker else pd.DataFrame(index=raw_prices.index)

        if ticker in raw_prices.columns.get_level_values(-1):
            return raw_prices.xs(ticker, axis=1, level=-1, drop_level=True)

        if ticker in raw_prices.columns.get_level_values(0):
            return raw_prices.xs(ticker, axis=1, level=0, drop_level=True)

        return pd.DataFrame(index=raw_prices.index)
