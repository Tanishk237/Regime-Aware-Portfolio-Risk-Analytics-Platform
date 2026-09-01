from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from src.database.models import FIIDIIHistory, MarketFeature, MarketPrice, VIXHistory
from src.ingestion.vix_data import VIXDataFetcher


class MarketDataPersistence:
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

    @staticmethod
    def _stored_prices_cover_request(
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
        dates = [
            record["date"].date() if hasattr(record["date"], "date") else record["date"]
            for record in records
        ]
        return min(dates) <= start_date and max(dates) >= end_date

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
