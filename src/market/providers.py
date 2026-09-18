from __future__ import annotations

import time
from functools import lru_cache
import importlib
import hashlib
import math
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Iterable, Optional

import pandas as pd


@lru_cache(maxsize=1)
def _yfinance():
    return importlib.import_module("yfinance")


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

    def get_instrument_metadata(self, ticker: str) -> dict:
        raise MarketDataProviderError(
            f"{self.name} does not provide instrument metadata for {ticker}."
        )


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
        yf = _yfinance()
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
        yf = _yfinance()

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
        yf = _yfinance()
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

    def get_instrument_metadata(self, ticker: str) -> dict:
        yf = _yfinance()

        def fetch() -> dict:
            info = yf.Ticker(ticker).get_info()
            if not isinstance(info, dict) or not info:
                raise MarketDataProviderError(f"No instrument metadata returned for {ticker}.")
            return {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "exchange": info.get("exchange") or info.get("fullExchangeName"),
                "country": info.get("country"),
                "currency": info.get("currency"),
                "data_source": self.name,
            }

        return self._retry(fetch)

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


class DeterministicTestProvider(MarketDataProvider):
    """Offline provider for repeatable automated tests. Never enable in production."""

    name = "test-fixture"

    _sectors = {
        "RELIANCE.NS": ("Energy", "Oil & Gas Integrated"),
        "INFY.NS": ("Technology", "Information Technology Services"),
        "TCS.NS": ("Technology", "Information Technology Services"),
        "HDFCBANK.NS": ("Financial Services", "Banks - Regional"),
        "ICICIBANK.NS": ("Financial Services", "Banks - Regional"),
        "SBIN.NS": ("Financial Services", "Banks - Regional"),
        "MARUTI.NS": ("Consumer Cyclical", "Auto Manufacturers"),
    }

    def get_ohlcv(
        self,
        tickers: list[str],
        start_date: date,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        if len(tickers) != 1:
            raise MarketDataProviderError("The test provider accepts one ticker per call.")
        ticker = tickers[0]
        final_date = end_date or date.today()
        index = pd.bdate_range(start=start_date, end=final_date)
        if index.empty:
            index = pd.DatetimeIndex([pd.Timestamp(start_date)])
        seed = int(hashlib.sha256(ticker.encode("utf-8")).hexdigest()[:8], 16)
        base = 600 + seed % 2_400
        rows = []
        for day_index, _ in enumerate(index):
            trend = 1 + 0.00025 * day_index
            cycle = 1 + 0.035 * math.sin(day_index / 17 + seed % 11)
            stress = 1 - 0.12 * math.exp(-((day_index - 130) / 28) ** 2)
            close = max(base * 0.5, base * trend * cycle * stress)
            rows.append(
                {
                    "Open": close * 0.997,
                    "High": close * 1.009,
                    "Low": close * 0.991,
                    "Close": close,
                    "Volume": 750_000 + (seed % 20) * 25_000 + day_index * 250,
                }
            )
        return pd.DataFrame(rows, index=index)

    def get_live_price(
        self,
        ticker: str,
        *,
        include_name: bool = False,
    ) -> dict:
        history = self.get_ohlcv([ticker], date.today() - timedelta(days=7))
        return {
            "ticker": ticker,
            "price": float(history["Close"].iloc[-1]),
            "name": f"{ticker} test fixture" if include_name else None,
        }

    def get_india_vix(
        self,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        index = pd.bdate_range(start=start_date, end=end_date or date.today())
        if index.empty:
            index = pd.DatetimeIndex([pd.Timestamp(start_date)])
        values = [17 + 2.5 * math.sin(index_value / 21) for index_value in range(len(index))]
        return pd.DataFrame({"vix": values}, index=index)

    def get_instrument_metadata(self, ticker: str) -> dict:
        sector, industry = self._sectors.get(ticker, ("Unclassified", "Unclassified"))
        return {
            "ticker": ticker,
            "name": f"{ticker} test fixture",
            "sector": sector,
            "industry": industry,
            "exchange": "NSE" if ticker.endswith(".NS") else "TEST",
            "country": "India",
            "currency": "INR",
            "data_source": self.name,
        }


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
    if provider_name.lower() == "test-fixture":
        return DeterministicTestProvider()
    raise ValueError(f"Unsupported market data provider: {provider_name}")
