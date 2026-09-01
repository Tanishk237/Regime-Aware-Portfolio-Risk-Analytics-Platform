from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from fastapi import status

from src.api.errors import AppError
from src.features.feature_builder import FeatureBuilder
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

        warnings = []
        try:
            price_records = self.get_historical_prices(
                normalized_tickers,
                start_date,
                end_date,
                persist=persist,
            )
            prices = self._price_records_to_frame(price_records)
            returns = prices.pct_change().dropna()
            if returns.empty:
                raise AppError(
                    "Not enough price history was available to build market features.",
                    code="INSUFFICIENT_MARKET_FEATURE_DATA",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            vix = self._optional_vix_frame(
                start_date=start_date,
                end_date=end_date,
                persist=persist,
                warnings=warnings,
            )
            flows = self._optional_flow_frame(
                filepath=fii_dii_path,
                start_date=start_date,
                end_date=end_date,
                warnings=warnings,
            )
            merged = self._merge_feature_inputs(returns, vix, flows)
            feature_matrix, metadata = FeatureBuilder().build(merged, weights=weights)
            if feature_matrix.empty:
                raise AppError(
                    "Not enough clean feature rows were available for regime analytics.",
                    code="INSUFFICIENT_REGIME_FEATURES",
                    status_code=422,
                    details={
                        "price_return_rows": len(returns),
                        "merged_rows": len(merged),
                    },
                )
        except AppError:
            raise
        except Exception as exc:
            raise self._market_data_error("Unable to build market feature matrix.", exc) from exc

        validation = self._json_ready(MarketDataValidator.validate_feature_matrix(feature_matrix))
        metadata = self._json_ready(metadata)
        metadata["warnings"] = warnings
        metadata["fallback_used"] = bool(warnings)
        metadata["price_rows"] = len(price_records)
        metadata["merged_rows"] = len(merged)

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

    def _optional_vix_frame(
        self,
        *,
        start_date: date,
        end_date: Optional[date],
        persist: bool,
        warnings: list[str],
    ) -> pd.DataFrame:
        try:
            vix_records = self.get_india_vix(start_date, end_date, window=5, persist=persist)
            return self._vix_records_to_frame(vix_records)
        except AppError as exc:
            warnings.append(f"India VIX unavailable: {exc.message}")
            return pd.DataFrame()
        except Exception as exc:
            warnings.append(f"India VIX unavailable: {exc}")
            return pd.DataFrame()

    def _optional_flow_frame(
        self,
        *,
        filepath: Optional[str],
        start_date: date,
        end_date: Optional[date],
        warnings: list[str],
    ) -> pd.DataFrame:
        try:
            return self._flow_frame_for_features(
                filepath=filepath,
                start_date=start_date,
                end_date=end_date,
            )
        except AppError as exc:
            warnings.append(f"FII/DII flows unavailable: {exc.message}")
            return pd.DataFrame()
        except Exception as exc:
            warnings.append(f"FII/DII flows unavailable: {exc}")
            return pd.DataFrame()

    @staticmethod
    def _merge_feature_inputs(
        returns: pd.DataFrame,
        vix: pd.DataFrame,
        flows: pd.DataFrame,
    ) -> pd.DataFrame:
        merged = returns.sort_index().copy()
        for frame in (vix, flows):
            if not frame.empty:
                merged = merged.join(frame.sort_index(), how="left")
        merged = merged.replace([float("inf"), float("-inf")], pd.NA).ffill().dropna(how="all")
        return merged

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
