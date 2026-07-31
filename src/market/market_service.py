from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from fastapi import status
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.database.models import FIIDIIHistory, MarketFeature, MarketPrice, VIXHistory
from src.features.feature_builder import FeatureBuilder
from src.ingestion.data_merger import DataMerger
from src.ingestion.fii_dii_data import FIIDIIDataFetcher
from src.ingestion.vix_data import VIXDataFetcher
from src.market.cache import InMemoryMarketDataCache, MarketDataCache
from src.market.providers import MarketDataProvider, build_market_data_provider
from src.market.validators import MarketDataValidator


logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(
        self,
        db: Session,
        *,
        default_fii_dii_path: str = "data/external/fii_dii.csv",
        provider: Optional[MarketDataProvider] = None,
        provider_name: str = "yahoo",
        cache: Optional[MarketDataCache] = None,
        cache_ttl_seconds: int = 900,
        provider_retries: int = 3,
        provider_retry_backoff_seconds: float = 0.25,
    ):
        self.db = db
        self.default_fii_dii_path = Path(default_fii_dii_path)
        self.provider = provider or build_market_data_provider(
            provider_name,
            retries=provider_retries,
            retry_backoff_seconds=provider_retry_backoff_seconds,
        )
        self.cache = cache or InMemoryMarketDataCache()
        self.cache_ttl_seconds = cache_ttl_seconds

    def get_historical_prices(
        self,
        tickers: Iterable[str],
        start_date: date,
        end_date: Optional[date] = None,
        *,
        persist: bool = True,
    ) -> list[dict]:
        self._validate_date_range(start_date, end_date)
        normalized_tickers = self._normalize_tickers(tickers)
        cache_key = self._cache_key("historical", normalized_tickers, start_date, end_date)
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("Market data cache hit for %s", cache_key)
            return cached

        stored = self._get_stored_prices(normalized_tickers, start_date, end_date)
        if self._stored_prices_cover_request(stored, normalized_tickers, start_date, end_date):
            logger.info("Market data DB hit for historical prices: %s", normalized_tickers)
            self.cache.set(cache_key, stored, self.cache_ttl_seconds)
            return stored

        try:
            refresh_records = self._fetch_missing_price_records(normalized_tickers, start_date, end_date, stored)
            MarketDataValidator.validate_ohlcv_records(refresh_records)
            if persist:
                self._upsert_market_prices(refresh_records)
        except AppError:
            raise
        except Exception as exc:
            if stored:
                logger.warning("Historical provider failed; serving stored prices. %s", exc)
                self.cache.set(cache_key, stored, self.cache_ttl_seconds)
                return stored
            raise self._market_data_error("Unable to fetch historical prices.", exc) from exc

        records = self._get_stored_prices(normalized_tickers, start_date, end_date)
        if not records:
            raise AppError(
                "No historical price data was returned for the requested tickers and date range.",
                code="MARKET_DATA_EMPTY",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.cache.set(cache_key, records, self.cache_ttl_seconds)
        return records

    def get_live_prices(
        self,
        tickers: Iterable[str],
        *,
        include_name: bool = False,
    ) -> list[dict]:
        records = []

        for ticker in self._normalize_tickers(tickers):
            cache_key = self._cache_key("live", [ticker], None, None, include_name)
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info("Market data cache hit for %s", cache_key)
                records.append(cached)
                continue
            try:
                record = self.provider.get_live_price(ticker, include_name=include_name)
                self.cache.set(cache_key, record, self.cache_ttl_seconds)
                records.append(record)
            except Exception as exc:
                fallback = self._get_latest_stored_price(ticker)
                if fallback is not None:
                    logger.warning("Live provider failed; serving latest stored close for %s. %s", ticker, exc)
                    record = {
                        "ticker": ticker,
                        "price": fallback["close"],
                        "name": None,
                    }
                    records.append(record)
                    continue
                raise self._market_data_error(f"Unable to fetch live price for {ticker}.", exc) from exc

        return records

    def get_india_vix(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        *,
        window: int = 5,
        persist: bool = True,
    ) -> list[dict]:
        self._validate_date_range(start_date, end_date)
        if window <= 0:
            raise AppError(
                "VIX change window must be greater than zero.",
                code="INVALID_VIX_WINDOW",
                status_code=422,
            )

        cache_key = self._cache_key("vix", ["^INDIAVIX"], start_date, end_date, window)
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("Market data cache hit for %s", cache_key)
            return cached

        stored = self._get_stored_vix(start_date, end_date, window)
        if self._stored_vix_covers_request(stored, start_date, end_date):
            self.cache.set(cache_key, stored, self.cache_ttl_seconds)
            return stored

        try:
            vix = self.provider.get_india_vix(start_date, end_date)
            vix = VIXDataFetcher.add_vix_change(vix, window=window)
            records = self._normalize_vix_records(vix, window)
            MarketDataValidator.validate_vix_records(records)
            if persist:
                self._upsert_vix(records)
        except Exception as exc:
            if stored:
                logger.warning("VIX provider failed; serving stored VIX data. %s", exc)
                self.cache.set(cache_key, stored, self.cache_ttl_seconds)
                return stored
            raise self._market_data_error("Unable to fetch India VIX history.", exc) from exc

        records = self._get_stored_vix(start_date, end_date, window)

        if not records:
            raise AppError(
                "No India VIX data was returned for the requested date range.",
                code="MARKET_DATA_EMPTY",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.cache.set(cache_key, records, self.cache_ttl_seconds)
        return records

    def get_fii_dii_flows(
        self,
        *,
        filepath: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        window: int = 20,
        persist: bool = True,
    ) -> list[dict]:
        self._validate_date_range(start_date, end_date)
        if window <= 0:
            raise AppError(
                "Flow rolling window must be greater than zero.",
                code="INVALID_FLOW_WINDOW",
                status_code=422,
            )

        path = Path(filepath) if filepath else self.default_fii_dii_path
        if not path.exists():
            raise AppError(
                "FII/DII flow file was not found.",
                code="FII_DII_FILE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"path": str(path)},
            )

        try:
            flows = FIIDIIDataFetcher.load(path)
            flows = FIIDIIDataFetcher.add_net_flow(flows)
            flows = FIIDIIDataFetcher.add_rolling_features(flows, window=window)
        except Exception as exc:
            raise AppError(
                "Unable to load FII/DII flow data.",
                code="FII_DII_LOAD_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"error": str(exc)},
            ) from exc

        flows = self._filter_date_range(flows, start_date, end_date)
        required_columns = {"fii", "dii", "net_flow"}
        if not required_columns.issubset(flows.columns):
            raise AppError(
                "FII/DII flow data is missing required columns.",
                code="FII_DII_INVALID",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"required_columns": sorted(required_columns)},
            )

        records = []
        for row_date, row in flows.dropna(subset=["fii", "dii", "net_flow"]).iterrows():
            records.append(
                {
                    "date": self._to_date(row_date),
                    "fii": float(row["fii"]),
                    "dii": float(row["dii"]),
                    "net_flow": float(row["net_flow"]),
                    "fii_avg": self._optional_float(row.get(f"fii_avg_{window}")),
                    "dii_avg": self._optional_float(row.get(f"dii_avg_{window}")),
                    "net_flow_avg": self._optional_float(row.get(f"net_flow_avg_{window}")),
                }
            )

        if not records:
            raise AppError(
                "No FII/DII flow data was available for the requested date range.",
                code="FII_DII_EMPTY",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if persist:
            self._upsert_fii_dii(records)

        return records

    def get_market_index_data(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        *,
        persist: bool = True,
    ) -> list[dict]:
        self._validate_date_range(start_date, end_date)
        return self.get_historical_prices(
            [self._normalize_symbol(symbol)],
            start_date,
            end_date,
            persist=persist,
        )

    def build_feature_matrix(
        self,
        *,
        tickers: Iterable[str],
        start_date: date,
        end_date: Optional[date] = None,
        weights: Optional[list[float]] = None,
        fii_dii_path: Optional[str] = None,
        persist: bool = True,
    ) -> dict:
        self._validate_date_range(start_date, end_date)
        normalized_tickers = self._normalize_tickers(tickers)
        if weights is not None and len(weights) != len(normalized_tickers):
            raise AppError(
                "Weights length must match ticker count.",
                code="WEIGHTS_TICKERS_MISMATCH",
                status_code=422,
            )

        weights = self._normalize_weights(weights) if weights is not None else None

        try:
            price_records = self.get_historical_prices(
                normalized_tickers,
                start_date,
                end_date,
                persist=persist,
            )
            prices = self._price_records_to_frame(price_records)
            returns = prices.pct_change().dropna()
            vix_records = self.get_india_vix(start_date, end_date, window=5, persist=persist)
            vix = self._vix_records_to_frame(vix_records)
            flows = self._flow_frame_for_features(
                filepath=fii_dii_path,
                start_date=start_date,
                end_date=end_date,
            )
            merged = DataMerger.clean(DataMerger.merge(returns, vix, flows))
            feature_matrix, metadata = FeatureBuilder().build(merged, weights=weights)
        except AppError:
            raise
        except Exception as exc:
            raise self._market_data_error("Unable to build market feature matrix.", exc) from exc

        validation = self._json_ready(MarketDataValidator.validate_feature_matrix(feature_matrix))
        metadata = self._json_ready(metadata)

        records = [
            {
                "date": self._to_date(index),
                "values": {column: float(value) for column, value in row.items()},
            }
            for index, row in feature_matrix.iterrows()
        ]

        if persist:
            self._upsert_market_features(merged, feature_matrix)

        return {
            "tickers": normalized_tickers,
            "start_date": start_date,
            "end_date": end_date,
            "columns": list(feature_matrix.columns),
            "records": records,
            "metadata": metadata,
            "validation": validation,
        }

    def _fetch_missing_price_records(
        self,
        tickers: list[str],
        start_date: date,
        end_date: Optional[date],
        stored: list[dict],
    ) -> list[dict]:
        records = []
        stored_by_ticker: dict[str, list[dict]] = {ticker: [] for ticker in tickers}
        for record in stored:
            stored_by_ticker.setdefault(record["ticker"], []).append(record)

        for ticker in tickers:
            existing = stored_by_ticker.get(ticker, [])
            missing_start = start_date
            if existing:
                latest = max(record["date"] for record in existing)
                missing_start = max(start_date, latest + timedelta(days=1))
            if end_date is not None and missing_start > end_date:
                continue
            raw_prices = self.provider.get_ohlcv([ticker], missing_start, end_date)
            records.extend(self._normalize_ohlcv(raw_prices, [ticker]))
        return records

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

    def _extract_ticker_ohlcv(
        self,
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

    def _get_stored_prices(
        self,
        tickers: list[str],
        start_date: date,
        end_date: Optional[date],
    ) -> list[dict]:
        query = (
            self.db.query(MarketPrice)
            .filter(MarketPrice.ticker.in_(tickers))
            .filter(MarketPrice.date >= start_date)
            .order_by(MarketPrice.ticker, MarketPrice.date)
        )
        if end_date is not None:
            query = query.filter(MarketPrice.date <= end_date)

        return [
            {
                "ticker": row.ticker,
                "date": row.date,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
            }
            for row in query.all()
        ]

    def _stored_prices_cover_request(
        self,
        records: list[dict],
        tickers: list[str],
        start_date: date,
        end_date: Optional[date],
    ) -> bool:
        if end_date is None:
            return False
        for ticker in tickers:
            ticker_records = [record for record in records if record["ticker"] == ticker]
            if not ticker_records:
                return False
            dates = [record["date"] for record in ticker_records]
            if min(dates) > start_date or max(dates) < end_date:
                return False
        return True

    def _get_latest_stored_price(self, ticker: str) -> Optional[dict]:
        row = (
            self.db.query(MarketPrice)
            .filter(MarketPrice.ticker == ticker)
            .order_by(MarketPrice.date.desc())
            .first()
        )
        if row is None:
            return None
        return {
            "ticker": row.ticker,
            "date": row.date,
            "close": row.close,
        }

    def _get_stored_vix(
        self,
        start_date: date,
        end_date: Optional[date],
        window: int,
    ) -> list[dict]:
        query = (
            self.db.query(VIXHistory)
            .filter(VIXHistory.date >= start_date)
            .order_by(VIXHistory.date)
        )
        if end_date is not None:
            query = query.filter(VIXHistory.date <= end_date)

        frame = pd.DataFrame(
            [{"date": row.date, "vix": row.vix} for row in query.all()]
        )
        if frame.empty:
            return []
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date")
        frame = VIXDataFetcher.add_vix_change(frame, window=window)
        return self._normalize_vix_records(frame, window)

    @staticmethod
    def _stored_vix_covers_request(
        records: list[dict],
        start_date: date,
        end_date: Optional[date],
    ) -> bool:
        if not records or end_date is None:
            return False
        dates = [record["date"] for record in records]
        return min(dates) <= start_date and max(dates) >= end_date

    @staticmethod
    def _price_records_to_frame(records: list[dict]) -> pd.DataFrame:
        frame = pd.DataFrame(records)
        if frame.empty:
            return pd.DataFrame()
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.pivot(index="date", columns="ticker", values="close").sort_index()

    @staticmethod
    def _vix_records_to_frame(records: list[dict]) -> pd.DataFrame:
        frame = pd.DataFrame(records)
        if frame.empty:
            return pd.DataFrame()
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.set_index("date")[["vix", "vix_change"]].rename(columns={"vix_change": "vix_change_5"})

    def _flow_frame_for_features(
        self,
        *,
        filepath: Optional[str],
        start_date: date,
        end_date: Optional[date],
    ) -> pd.DataFrame:
        path = Path(filepath) if filepath else self.default_fii_dii_path
        if not path.exists():
            raise AppError(
                "FII/DII flow file was not found.",
                code="FII_DII_FILE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"path": str(path)},
            )
        flows = FIIDIIDataFetcher.load(path)
        flows = FIIDIIDataFetcher.add_net_flow(flows)
        flows = FIIDIIDataFetcher.add_rolling_features(flows, window=20)
        return self._filter_date_range(flows, start_date, end_date)

    def _upsert_market_prices(self, records: list[dict]) -> None:
        for record in records:
            existing = (
                self.db.query(MarketPrice)
                .filter(MarketPrice.ticker == record["ticker"], MarketPrice.date == record["date"])
                .one_or_none()
            )
            if existing is None:
                self.db.add(MarketPrice(**record))
                continue
            for key in ("open", "high", "low", "close", "volume"):
                setattr(existing, key, record[key])
        self.db.commit()

    def _upsert_vix(self, records: list[dict]) -> None:
        for record in records:
            existing = self.db.query(VIXHistory).filter(VIXHistory.date == record["date"]).one_or_none()
            if existing is None:
                self.db.add(VIXHistory(date=record["date"], vix=record["vix"]))
            else:
                existing.vix = record["vix"]
        self.db.commit()

    def _upsert_fii_dii(self, records: list[dict]) -> None:
        for record in records:
            existing = (
                self.db.query(FIIDIIHistory)
                .filter(FIIDIIHistory.date == record["date"])
                .one_or_none()
            )
            if existing is None:
                self.db.add(
                    FIIDIIHistory(
                        date=record["date"],
                        fii=record["fii"],
                        dii=record["dii"],
                        net_flow=record["net_flow"],
                    )
                )
            else:
                existing.fii = record["fii"]
                existing.dii = record["dii"]
                existing.net_flow = record["net_flow"]
        self.db.commit()

    def _upsert_market_features(
        self,
        merged: pd.DataFrame,
        feature_matrix: pd.DataFrame,
    ) -> None:
        for row_date, row in merged.iterrows():
            feature_row = feature_matrix.loc[row_date] if row_date in feature_matrix.index else {}
            vix_change_column = next((column for column in merged.columns if column.startswith("vix_change")), None)
            market_return_column = next((column for column in merged.columns if column.startswith("^")), None)
            record = {
                "date": self._to_date(row_date),
                "vix": self._optional_float(row.get("vix")),
                "vix_change": self._optional_float(row.get(vix_change_column)) if vix_change_column else None,
                "net_flow": self._optional_float(row.get("net_flow")),
                "volatility": self._optional_float(feature_row.get("volatility_20")) if hasattr(feature_row, "get") else None,
                "market_return": self._optional_float(row.get(market_return_column)) if market_return_column else None,
            }
            existing = self.db.query(MarketFeature).filter(MarketFeature.date == record["date"]).one_or_none()
            if existing is None:
                self.db.add(MarketFeature(**record))
                continue
            for key, value in record.items():
                if key != "date":
                    setattr(existing, key, value)
        self.db.commit()

    @staticmethod
    def _normalize_tickers(tickers: Iterable[str]) -> list[str]:
        normalized = [MarketDataService._normalize_symbol(ticker) for ticker in tickers if ticker and ticker.strip()]
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
            return {key: MarketDataService._json_ready(item) for key, item in value.items()}
        if isinstance(value, list):
            return [MarketDataService._json_ready(item) for item in value]
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
