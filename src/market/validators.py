from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import status

from src.api.errors import AppError


class MarketDataValidator:
    @staticmethod
    def validate_ohlcv_records(records: list[dict]) -> None:
        seen: set[tuple[str, date]] = set()
        errors = []

        for record in records:
            key = (record["ticker"], record["date"])
            if key in seen:
                errors.append({"record": key, "issue": "duplicate ticker/date"})
            seen.add(key)

            close = record.get("close")
            if close is None or pd.isna(close) or close <= 0:
                errors.append({"record": key, "issue": "close must be positive"})

            high = record.get("high")
            low = record.get("low")
            if high is not None and low is not None and high < low:
                errors.append({"record": key, "issue": "high cannot be lower than low"})

            for field in ("open", "high", "low"):
                value = record.get(field)
                if value is not None and value <= 0:
                    errors.append({"record": key, "issue": f"{field} must be positive"})

            volume = record.get("volume")
            if volume is not None and volume < 0:
                errors.append({"record": key, "issue": "volume cannot be negative"})

        if errors:
            raise AppError(
                "Market price data failed validation.",
                code="MARKET_DATA_VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                details={"errors": errors[:20]},
            )

    @staticmethod
    def validate_vix_records(records: list[dict]) -> None:
        seen: set[date] = set()
        errors = []
        for record in records:
            row_date = record["date"]
            if row_date in seen:
                errors.append({"date": str(row_date), "issue": "duplicate date"})
            seen.add(row_date)
            if record.get("vix") is None or record["vix"] <= 0:
                errors.append({"date": str(row_date), "issue": "vix must be positive"})

        if errors:
            raise AppError(
                "India VIX data failed validation.",
                code="MARKET_DATA_VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                details={"errors": errors[:20]},
            )

    @staticmethod
    def validate_feature_matrix(feature_matrix: pd.DataFrame) -> dict:
        report = {
            "rows": int(len(feature_matrix)),
            "columns": int(len(feature_matrix.columns)),
            "missing_values": int(feature_matrix.isna().sum().sum()),
            "duplicate_index": int(feature_matrix.index.duplicated().sum()),
            "infinite_values": int(
                feature_matrix.isin([float("inf"), float("-inf")]).sum().sum()
            ),
            "feature_names": list(feature_matrix.columns),
        }
        report["is_valid"] = (
            report["rows"] > 0
            and report["missing_values"] == 0
            and report["duplicate_index"] == 0
            and report["infinite_values"] == 0
        )
        return report
