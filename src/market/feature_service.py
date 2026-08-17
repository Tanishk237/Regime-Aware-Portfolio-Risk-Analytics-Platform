from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from fastapi import status

from src.api.errors import AppError
from src.features.feature_builder import FeatureBuilder
from src.ingestion.data_merger import DataMerger
from src.ingestion.fii_dii_data import FIIDIIDataFetcher
from src.market.validators import MarketDataValidator


class MarketFeatureService:
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
