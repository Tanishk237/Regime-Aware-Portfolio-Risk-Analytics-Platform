import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.portfolio.portfolio_returns import PortfolioReturnEngine


def test_portfolio_return_engine_builds_weighted_returns_and_summary():
    price_history = pd.DataFrame(
        {
            "RELIANCE.NS": [100, 102, 101, 105, 107],
            "INFY.NS": [50, 51, 52, 51, 53],
        },
        index=pd.date_range(start="2024-01-01", periods=5),
    )
    weights = {
        "RELIANCE.NS": 0.60,
        "INFY.NS": 0.40,
    }

    engine = PortfolioReturnEngine()
    asset_returns = engine.calculate_asset_returns(price_history)
    portfolio_returns = engine.build_returns(price_history, weights)
    cumulative_returns = engine.build_cumulative_returns(portfolio_returns)
    summary = engine.portfolio_summary(portfolio_returns)

    expected_returns = asset_returns.mul(
        pd.Series(weights),
        axis=1,
    ).sum(axis=1)

    pd.testing.assert_series_equal(
        portfolio_returns,
        expected_returns.rename("portfolio_return"),
    )
    assert cumulative_returns.iloc[-1] == pytest.approx(1.0665803062586803)
    assert summary["total_return"] == pytest.approx(0.06658030625868028)
    assert np.isfinite(summary["annualized_return"])
    assert np.isfinite(summary["annualized_volatility"])


def test_portfolio_return_engine_rejects_invalid_weights():
    price_history = pd.DataFrame(
        {
            "RELIANCE.NS": [100, 102],
            "INFY.NS": [50, 51],
        }
    )

    with pytest.raises(ValueError, match="Weights must sum to 1"):
        PortfolioReturnEngine().build_returns(
            price_history,
            {
                "RELIANCE.NS": 0.7,
                "INFY.NS": 0.4,
            },
        )
