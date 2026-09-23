from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Iterable

from src.market.sector_taxonomy import resolve_sector


logger = logging.getLogger(__name__)


class InstrumentMetadataService:
    def get_instrument_metadata(
        self,
        tickers: Iterable[str],
        *,
        refresh: bool = False,
    ) -> list[dict]:
        requested = [ticker for ticker in tickers if ticker and ticker.strip()]
        if not requested:
            return []
        normalized = self._normalize_tickers(requested)

        resolved: dict[str, dict] = {}
        unresolved: list[str] = []
        for ticker in normalized:
            cache_key = self._cache_key("instrument-metadata", [ticker], None, None)
            cached = None if refresh else self.cache.get(cache_key)
            if cached is None:
                unresolved.append(ticker)
            else:
                resolved[ticker] = self._classify_record(cached, ticker)

        stored_records = self._get_stored_instrument_metadata(unresolved)
        stored = {
            record["ticker"]: self._classify_record(record, record["ticker"])
            for record in stored_records
        }
        corrections = [
            stored[record["ticker"]]
            for record in stored_records
            if stored[record["ticker"]]["sector"] != record.get("sector")
        ]
        if corrections:
            self._upsert_instrument_metadata(corrections)
        stale_before = date.today() - timedelta(days=self.instrument_metadata_ttl_days)
        to_refresh = [
            ticker
            for ticker in unresolved
            if refresh
            or ticker not in stored
            or self._metadata_is_stale(stored[ticker], stale_before)
        ]

        fetched = self._fetch_instrument_metadata(to_refresh)
        if fetched:
            self._upsert_instrument_metadata(fetched)
            stored.update(
                {
                    record["ticker"]: record
                    for record in self._get_stored_instrument_metadata(to_refresh)
                }
            )

        for ticker in unresolved:
            record = stored.get(ticker) or self._classify_record(
                {
                    "ticker": ticker,
                    "name": None,
                    "sector": None,
                    "industry": None,
                    "exchange": None,
                    "country": None,
                    "currency": None,
                    "data_source": "unavailable",
                    "updated_at": None,
                },
                ticker,
            )
            resolved[ticker] = record
            cache_key = self._cache_key("instrument-metadata", [ticker], None, None)
            self.cache.set(cache_key, record, self.cache_ttl_seconds)

        return [resolved[ticker] for ticker in normalized]

    def _fetch_instrument_metadata(self, tickers: list[str]) -> list[dict]:
        if not tickers:
            return []

        records: list[dict] = []
        worker_count = min(4, len(tickers))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(self.provider.get_instrument_metadata, ticker): ticker
                for ticker in tickers
            }
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    record = future.result()
                except Exception as exc:
                    logger.warning(
                        "Instrument metadata provider failed for %s; using stored or local classification. %s",
                        ticker,
                        exc,
                    )
                    continue
                records.append(
                    self._classify_record(
                        {
                            **record,
                            "ticker": ticker,
                            "data_source": record.get("data_source")
                            or self.provider.name,
                            "updated_at": datetime.now(timezone.utc),
                        },
                        ticker,
                    )
                )
        return records

    @staticmethod
    def _classify_record(record: dict, ticker: str) -> dict:
        return {
            **record,
            "ticker": ticker,
            "sector": resolve_sector(
                ticker,
                record.get("sector"),
                record.get("industry"),
            ),
        }

    @staticmethod
    def _metadata_is_stale(record: dict, stale_before: date) -> bool:
        updated_at = record.get("updated_at")
        if updated_at is None:
            return True
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        if str(record.get("sector") or "").strip().lower() == "other":
            return updated_at.date() < date.today()
        return updated_at.date() < stale_before
