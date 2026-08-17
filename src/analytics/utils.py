from __future__ import annotations

import math
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from src.api.errors import AppError
from src.database.models import Position


class AnalyticsUtils:
    @staticmethod
    def _weights_from_positions(positions: list[Position]) -> list[float]:
        cost_basis = [float(position.cost_basis) for position in positions if position.quantity > 0]
        total = sum(cost_basis)
        if not total:
            return [1 / len(cost_basis)] * len(cost_basis)
        return [value / total for value in cost_basis]

    @staticmethod
    def _feature_records_to_frame(records: list[dict]) -> pd.DataFrame:
        frame = pd.DataFrame(
            [{"date": record["date"], **record["values"]} for record in records]
        )
        if frame.empty:
            return pd.DataFrame()
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.set_index("date").sort_index()

    @staticmethod
    def _series_to_records(series: pd.Series, value_name: str) -> list[dict]:
        return [
            {
                "date": pd.Timestamp(row_date).date(),
                value_name: float(value),
            }
            for row_date, value in series.dropna().items()
        ]

    @staticmethod
    def _dataframe_to_matrix(frame: pd.DataFrame) -> list[list[float]]:
        return [[float(value) for value in row] for row in frame.values]

    @staticmethod
    def _estimate_transition_matrix(states: pd.Series, state_count: int) -> pd.DataFrame:
        matrix = np.zeros((state_count, state_count), dtype=float)
        values = states.astype(int).tolist()
        for current, nxt in zip(values, values[1:]):
            matrix[current, nxt] += 1
        for state in range(state_count):
            total = matrix[state].sum()
            if total == 0:
                matrix[state, state] = 1.0
            else:
                matrix[state] = matrix[state] / total
        return pd.DataFrame(matrix, index=range(state_count), columns=range(state_count))

    @staticmethod
    def _safe_div(numerator: float, denominator: Optional[float]) -> Optional[float]:
        if denominator is None or denominator == 0 or pd.isna(denominator):
            return None
        return float(numerator / denominator)

    @staticmethod
    def _normal_pdf(value: float) -> float:
        return math.exp(-(value**2) / 2) / math.sqrt(2 * math.pi)

    @staticmethod
    def _optional_float(value) -> Optional[float]:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _to_date(value) -> date:
        if isinstance(value, date):
            return value
        return pd.Timestamp(value).date()

    @staticmethod
    def _validate_date_range(start_date: Optional[date], end_date: Optional[date]) -> None:
        if start_date is not None and end_date is not None and end_date < start_date:
            raise AppError(
                "end_date must be greater than or equal to start_date.",
                code="INVALID_DATE_RANGE",
                status_code=422,
            )

    @staticmethod
    def _health_score(metrics: dict) -> float:
        score = 100
        score -= min(abs(metrics["max_drawdown"]) * 100, 40)
        score -= min(metrics["annualized_volatility"] * 50, 30)
        if metrics["sharpe"] is not None:
            score += max(min(metrics["sharpe"] * 5, 10), -10)
        return float(max(0, min(100, score)))
