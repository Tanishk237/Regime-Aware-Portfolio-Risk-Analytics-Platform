from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Iterable, Optional

import pandas as pd
import yfinance as yf


class MarketDataProviderError(Exception):
    pass


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def get_ohlcv(
        self,
        tickers: list[str],
        start_date: date,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_live_price(
        self,
        ticker: str,
        *,
        include_name: bool = False,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_india_vix(
        self,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError


class YahooFinanceProvider(MarketDataProvider):
    name = "yahoo"

    def __init__(
        self,
        *,
        retries: int = 3,
        retry_backoff_seconds: float = 0.25,
    ):
        self.retries = retries
        self.retry_backoff_seconds = retry_backoff_seconds

    def get_ohlcv(
        self,
        tickers: list[str],
        start_date: date,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        query = tickers if len(tickers) > 1 else tickers[0]
        inclusive_end = end_date + timedelta(days=1) if end_date is not None else None
        return self._retry(
            lambda: yf.download(
                query,
                start=start_date,
                end=inclusive_end,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        )

    def get_live_price(
        self,
        ticker: str,
        *,
        include_name: bool = False,
    ) -> dict:
        def fetch() -> dict:
            data = yf.Ticker(ticker)
            history = data.history(period="1d")
            if history.empty or "Close" not in history.columns:
                raise MarketDataProviderError(f"No live price returned for {ticker}.")
            payload = {
                "ticker": ticker,
                "price": float(history["Close"].iloc[-1]),
                "name": None,
            }
            if include_name:
                payload["name"] = data.info.get("longName", "Unknown")
            return payload

        return self._retry(fetch)

    def get_india_vix(
        self,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        inclusive_end = end_date + timedelta(days=1) if end_date is not None else None
        data = self._retry(
            lambda: yf.download(
                "^INDIAVIX",
                start=start_date,
                end=inclusive_end,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        )
        return self._normalize_vix(data)

    def _retry(self, operation):
        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                return operation()
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.retry_backoff_seconds * attempt)
        raise MarketDataProviderError(str(last_error)) from last_error

    @staticmethod
    def _normalize_vix(data: pd.DataFrame) -> pd.DataFrame:
        if isinstance(data.columns, pd.MultiIndex) and "Close" in data.columns.get_level_values(0):
            data = data["Close"]

        if isinstance(data, pd.Series):
            return data.to_frame(name="vix")

        data = data.copy()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [
                column[-1] if isinstance(column, tuple) and len(column) > 1 else column
                for column in data.columns
            ]
        if "Close" in data.columns:
            return data[["Close"]].rename(columns={"Close": "vix"})
        if data.shape[1] == 1:
            data.columns = ["vix"]
        return data


def build_market_data_provider(
    provider_name: str,
    *,
    retries: int = 3,
    retry_backoff_seconds: float = 0.25,
) -> MarketDataProvider:
    if provider_name.lower() == "yahoo":
        return YahooFinanceProvider(
            retries=retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    raise ValueError(f"Unsupported market data provider: {provider_name}")
