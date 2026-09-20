import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.risk_service import AnalyticsRiskService
from src.analytics.utils import AnalyticsUtils
from src.api.errors import AppError


class RiskMetricHarness(AnalyticsRiskService, AnalyticsUtils):
    pass


def dated_returns(values: list[float]) -> pd.Series:
    return pd.Series(
        values,
        index=pd.date_range("2025-01-01", periods=len(values), freq="B"),
        dtype=float,
    )


def test_risk_metrics_and_series_share_the_same_compounded_return():
    calculator = RiskMetricHarness()
    returns = dated_returns([-0.10, 0.04, -0.02, 0.03, 0.01])

    metrics = calculator._calculate_risk_metrics(
        returns,
        confidence_level=0.95,
        risk_free_rate=0.06,
    )
    series = calculator._build_risk_series(returns, rolling_window=3)

    expected_total_return = float((1 + returns).prod() - 1)
    assert metrics["period_return"] == pytest.approx(expected_total_return)
    assert metrics["total_return"] == pytest.approx(expected_total_return)
    assert series["cumulative_returns"][-1]["cumulative_return"] == pytest.approx(
        expected_total_return
    )
    assert metrics["max_drawdown"] == pytest.approx(
        min(point["drawdown"] for point in series["drawdown"])
    )
    assert metrics["historical_cvar"] <= metrics["historical_var"]
    assert metrics["parametric_cvar"] <= metrics["parametric_var"]
    assert metrics["annualized_volatility"] >= 0


def test_drawdown_includes_starting_capital_as_the_first_peak():
    calculator = RiskMetricHarness()
    returns = dated_returns([-0.10, 0.05])

    metrics = calculator._calculate_risk_metrics(
        returns,
        confidence_level=0.95,
        risk_free_rate=0.0,
    )
    series = calculator._build_risk_series(returns, rolling_window=2)

    assert series["drawdown"][0]["drawdown"] == pytest.approx(-0.10)
    assert metrics["max_drawdown"] == pytest.approx(-0.10)


def test_parametric_metrics_honor_any_valid_confidence_level():
    calculator = RiskMetricHarness()
    returns = dated_returns([-0.03, -0.01, 0.0, 0.01, 0.03])

    ninety = calculator._calculate_risk_metrics(
        returns,
        confidence_level=0.90,
        risk_free_rate=0.0,
    )
    custom = calculator._calculate_risk_metrics(
        returns,
        confidence_level=0.975,
        risk_free_rate=0.0,
    )

    assert custom["parametric_var"] < ninety["parametric_var"]
    assert custom["parametric_cvar"] < ninety["parametric_cvar"]


@pytest.mark.parametrize(
    ("values", "confidence_level", "risk_free_rate", "code"),
    [
        ([0.01, np.inf], 0.95, 0.0, "INVALID_RETURNS"),
        ([0.01, -1.0], 0.95, 0.0, "INVALID_RETURNS"),
        ([0.01, 0.02], 1.0, 0.0, "INVALID_CONFIDENCE_LEVEL"),
        ([0.01, 0.02], 0.95, -1.0, "INVALID_RISK_FREE_RATE"),
    ],
)
def test_risk_metrics_reject_invalid_inputs(
    values: list[float],
    confidence_level: float,
    risk_free_rate: float,
    code: str,
):
    calculator = RiskMetricHarness()

    with pytest.raises(AppError) as exc:
        calculator._calculate_risk_metrics(
            dated_returns(values),
            confidence_level=confidence_level,
            risk_free_rate=risk_free_rate,
        )

    assert exc.value.code == code


def test_constant_returns_never_emit_nan_or_infinity():
    calculator = RiskMetricHarness()
    metrics = calculator._calculate_risk_metrics(
        dated_returns([0.01] * 20),
        confidence_level=0.95,
        risk_free_rate=0.0,
    )

    assert metrics["sharpe"] is None
    assert metrics["sortino"] is None
    assert all(
        value is None or math.isfinite(value)
        for value in metrics.values()
    )
