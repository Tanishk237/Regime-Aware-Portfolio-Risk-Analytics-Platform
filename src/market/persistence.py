from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from src.database.models import (
    FIIDIIHistory,
    InstrumentMetadata,
    MarketFeature,
    MarketPrice,
    VIXHistory,
)
from src.database.upsert import upsert_rows
from src.ingestion.vix_data import VIXDataFetcher


class MarketDataPersistence:
    def _get_stored_instrument_metadata(self, tickers: list[str]) -> list[dict]:
        rows = (
            self.db.query(InstrumentMetadata)
            .filter(InstrumentMetadata.ticker.in_(tickers))
            .order_by(InstrumentMetadata.ticker)
            .all()
        )
        return [
            {
                "ticker": row.ticker,
                "name": row.name,
                "sector": row.sector,
                "industry": row.industry,
                "exchange": row.exchange,
                "country": row.country,
                "currency": row.currency,
                "data_source": row.data_source,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    def _upsert_instrument_metadata(self, records: list[dict]) -> None:
        upsert_rows(
            self.db,
            InstrumentMetadata,
            records,
            conflict_columns=("ticker",),
            update_columns=(
                "name",
                "sector",
                "industry",
                "exchange",
                "country",
                "currency",
                "data_source",
                "updated_at",
            ),
        )

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
        if not self.allow_demo_data:
            query = query.filter(MarketPrice.data_source != "demo")
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
                "source": row.data_source,
            }
            for row in query.all()
        ]

    @staticmethod
    def _stored_prices_cover_request(
        records: list[dict],
        tickers: list[str],
        start_date: date,
        end_date: Optional[date],
    ) -> bool:
        requested_start = MarketDataPersistence._next_weekday(start_date)
        requested_end = MarketDataPersistence._previous_weekday(end_date or date.today())
        for ticker in tickers:
            ticker_records = [record for record in records if record["ticker"] == ticker]
            if not ticker_records:
                return False
            dates = [record["date"] for record in ticker_records]
            if min(dates) > requested_start or max(dates) < requested_end:
                return False
        return True

    @staticmethod
    def _missing_price_ranges(
        records: list[dict],
        ticker: str,
        start_date: date,
        end_date: Optional[date],
    ) -> list[tuple[date, date]]:
        requested_start = MarketDataPersistence._next_weekday(start_date)
        requested_end = MarketDataPersistence._previous_weekday(end_date or date.today())
        if requested_start > requested_end:
            return []
        dates = [record["date"] for record in records if record["ticker"] == ticker]
        if not dates:
            return [(requested_start, requested_end)]

        earliest = min(dates)
        latest = max(dates)
        missing: list[tuple[date, date]] = []
        if earliest > requested_start:
            missing.append((requested_start, earliest - timedelta(days=1)))
        if latest < requested_end:
            missing.append((latest + timedelta(days=1), requested_end))
        return missing

    @staticmethod
    def _next_weekday(value: date) -> date:
        while value.weekday() >= 5:
            value += timedelta(days=1)
        return value

    @staticmethod
    def _previous_weekday(value: date) -> date:
        while value.weekday() >= 5:
            value -= timedelta(days=1)
        return value

    def _get_latest_stored_price(self, ticker: str) -> Optional[dict]:
        row = (
            self.db.query(MarketPrice)
            .filter(MarketPrice.ticker == ticker)
            .filter(MarketPrice.data_source != "demo")
            .order_by(MarketPrice.date.desc())
            .first()
        )
        if self.allow_demo_data:
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
            "data_source": row.data_source,
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
        dates = [
            record["date"].date() if hasattr(record["date"], "date") else record["date"]
            for record in records
        ]
        return min(dates) <= start_date and max(dates) >= end_date

    def _upsert_market_prices(self, records: list[dict]) -> None:
        upsert_rows(
            self.db,
            MarketPrice,
            [{**record, "data_source": "provider"} for record in records],
            conflict_columns=("ticker", "date"),
            update_columns=("open", "high", "low", "close", "volume", "data_source"),
        )

    def _upsert_vix(self, records: list[dict]) -> None:
        upsert_rows(
            self.db,
            VIXHistory,
            records,
            conflict_columns=("date",),
            update_columns=("vix",),
        )

    def _upsert_fii_dii(self, records: list[dict]) -> None:
        upsert_rows(
            self.db,
            FIIDIIHistory,
            records,
            conflict_columns=("date",),
            update_columns=("fii", "dii", "net_flow"),
        )

    def _upsert_market_features(
        self,
        merged: pd.DataFrame,
        feature_matrix: pd.DataFrame,
    ) -> None:
        records = []
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
            records.append(record)
        upsert_rows(
            self.db,
            MarketFeature,
            records,
            conflict_columns=("date",),
            update_columns=("vix", "vix_change", "net_flow", "volatility", "market_return"),
        )
