import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.portfolio_features import PortfolioFeatureBuilder


def test_portfolio_feature_builder_creates_expected_features():
    rng = np.random.RandomState(42)
    returns = pd.Series(
        rng.normal(0.001, 0.02, 250),
        index=pd.date_range("2024-01-01", periods=250),
        name="portfolio_return",
    )

    features = PortfolioFeatureBuilder(
        volatility_window=20
    ).build(returns)

    assert list(features.columns) == [
        "return",
        "volatility_20",
        "drawdown",
    ]
    assert len(features) == len(returns)
    assert features["volatility_20"].iloc[:19].isna().all()
    assert features["volatility_20"].iloc[19:].notna().all()
    assert features["drawdown"].max() <= 0
