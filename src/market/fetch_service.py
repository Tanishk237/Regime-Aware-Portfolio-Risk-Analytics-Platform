from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Optional

from fastapi import status

from src.api.errors import AppError
from src.ingestion.fii_dii_data import FIIDIIDataFetcher
from src.ingestion.vix_data import VIXDataFetcher
from src.market.validators import MarketDataValidator


logger = logging.getLogger(__name__)


class MarketDataFetchService:
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
        cache_key = self._cache_key(
            "historical",
            normalized_tickers,
            start_date,
            end_date,
            "include-demo" if self.allow_demo_data else "provider-only",
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("Market data cache hit for %s", cache_key)
            self._record_fetch_metadata(
                "historical",
                cached,
                source="cache",
                fallback_used=False,
                coverage_complete=self._stored_prices_cover_request(
                    cached, normalized_tickers, start_date, end_date
                ),
            )
            return cached

        stored = self._get_stored_prices(normalized_tickers, start_date, end_date)
        if self._stored_prices_cover_request(stored, normalized_tickers, start_date, end_date):
            logger.info("Market data DB hit for historical prices: %s", normalized_tickers)
            self.cache.set(cache_key, stored, self.cache_ttl_seconds)
            self._record_fetch_metadata(
                "historical",
                stored,
                source="stored",
                fallback_used=False,
                coverage_complete=True,
            )
            return stored

        refresh_records: list[dict] = []
        try:
            refresh_records = self._fetch_missing_price_records(normalized_tickers, start_date, end_date, stored)
            if refresh_records:
                MarketDataValidator.validate_ohlcv_records(refresh_records)
                if persist:
                    self._upsert_market_prices(refresh_records)
            elif not stored:
                raise AppError(
                    "No historical price data was returned for the requested tickers and date range.",
                    code="MARKET_DATA_EMPTY",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        except AppError:
            raise
        except Exception as exc:
            if stored:
                logger.warning("Historical provider failed and stored coverage is incomplete. %s", exc)
                raise AppError(
                    "Stored market data does not fully cover the requested range and the provider is unavailable.",
                    code="MARKET_DATA_INCOMPLETE",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    details=self._coverage_details(stored, normalized_tickers),
                ) from exc
            raise self._market_data_error("Unable to fetch historical prices.", exc) from exc

        if persist:
            records = self._get_stored_prices(normalized_tickers, start_date, end_date)
        else:
            records_by_key = {
                (record["ticker"], record["date"]): record for record in stored
            }
            for record in refresh_records:
                records_by_key[(record["ticker"], record["date"])] = {
                    **record,
                    "source": self.provider.name,
                }
            records = sorted(
                records_by_key.values(), key=lambda item: (item["ticker"], item["date"])
            )
        if not records:
            raise AppError(
                "No historical price data was returned for the requested tickers and date range.",
                code="MARKET_DATA_EMPTY",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.cache.set(cache_key, records, self.cache_ttl_seconds)
        coverage_complete = self._stored_prices_cover_request(
            records, normalized_tickers, start_date, end_date
        )
        self._record_fetch_metadata(
            "historical",
            records,
            source=self.provider.name if refresh_records else "stored",
            fallback_used=False,
            coverage_complete=coverage_complete,
        )
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
                as_of = self._to_date(record.get("as_of") or date.today())
                record = {
                    **record,
                    "source": self.provider.name,
                    "as_of": as_of,
                    "is_stale": self._quote_is_stale(as_of),
                }
                self.cache.set(cache_key, record, self.cache_ttl_seconds)
                records.append(record)
            except Exception as exc:
                fallback = self._get_latest_stored_price(ticker)
                if fallback is not None:
                    logger.warning("Live provider failed; serving latest stored close for %s. %s", ticker, exc)
                    records.append(
                        {
                            "ticker": ticker,
                            "price": fallback["close"],
                            "name": None,
                            "source": f"stored:{fallback.get('data_source') or 'unknown'}",
                            "as_of": fallback["date"],
                            "is_stale": self._quote_is_stale(fallback["date"]),
                        }
                    )
                    continue
                raise self._market_data_error(f"Unable to fetch live price for {ticker}.", exc) from exc

        return records

    @staticmethod
    def _quote_is_stale(as_of: date) -> bool:
        latest_session = date.today()
        while latest_session.weekday() >= 5:
            latest_session -= timedelta(days=1)
        return as_of < latest_session

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
            self._record_fetch_metadata(
                "vix",
                cached,
                source="cache",
                fallback_used=False,
                coverage_complete=self._stored_vix_covers_request(
                    cached, start_date, end_date
                ),
            )
            return cached

        stored = self._get_stored_vix(start_date, end_date, window)
        if self._stored_vix_covers_request(stored, start_date, end_date):
            self.cache.set(cache_key, stored, self.cache_ttl_seconds)
            self._record_fetch_metadata(
                "vix",
                stored,
                source="stored",
                fallback_used=False,
                coverage_complete=True,
            )
            return stored

        provider_records: list[dict] = []
        try:
            vix = self.provider.get_india_vix(start_date, end_date)
            vix = VIXDataFetcher.add_vix_change(vix, window=window)
            provider_records = self._normalize_vix_records(vix, window)
            MarketDataValidator.validate_vix_records(provider_records)
            if persist:
                self._upsert_vix(provider_records)
        except Exception as exc:
            if stored:
                logger.warning("VIX provider failed and stored coverage is incomplete. %s", exc)
                raise AppError(
                    "Stored India VIX data does not fully cover the requested range and the provider is unavailable.",
                    code="MARKET_DATA_INCOMPLETE",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    details=self._coverage_details(stored, ["^INDIAVIX"]),
                ) from exc
            raise self._market_data_error("Unable to fetch India VIX history.", exc) from exc

        records = (
            self._get_stored_vix(start_date, end_date, window)
            if persist
            else provider_records
        )

        if not records:
            raise AppError(
                "No India VIX data was returned for the requested date range.",
                code="MARKET_DATA_EMPTY",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.cache.set(cache_key, records, self.cache_ttl_seconds)
        self._record_fetch_metadata(
            "vix",
            records,
            source=self.provider.name,
            fallback_used=False,
            coverage_complete=self._stored_vix_covers_request(
                records, start_date, end_date
            ),
        )
        return records

    def _record_fetch_metadata(
        self,
        dataset: str,
        records: list[dict],
        *,
        source: str,
        fallback_used: bool,
        coverage_complete: bool,
    ) -> None:
        dates = [self._to_date(record["date"]) for record in records if record.get("date")]
        self.fetch_metadata[dataset] = {
            "source": source,
            "fallback_used": fallback_used,
            "coverage_complete": coverage_complete,
            "as_of": max(dates) if dates else None,
        }

    @staticmethod
    def _coverage_details(records: list[dict], tickers: list[str]) -> dict:
        available = {}
        for ticker in tickers:
            dates = [record["date"] for record in records if record.get("ticker") == ticker]
            if dates:
                available[ticker] = {
                    "start_date": str(min(dates)),
                    "end_date": str(max(dates)),
                }
        return {"available_ranges": available}

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

    def _fetch_missing_price_records(
        self,
        tickers: list[str],
        start_date: date,
        end_date: Optional[date],
        stored: list[dict],
    ) -> list[dict]:
        records: list[dict] = []

        for ticker in tickers:
            for missing_start, missing_end in self._missing_price_ranges(
                stored,
                ticker,
                start_date,
                end_date,
            ):
                raw_prices = self.provider.get_ohlcv(
                    [ticker],
                    missing_start,
                    missing_end,
                )
                normalized = self._normalize_ohlcv(raw_prices, [ticker])
                records.extend(
                    record
                    for record in normalized
                    if missing_start <= record["date"] <= missing_end
                )
        return records
