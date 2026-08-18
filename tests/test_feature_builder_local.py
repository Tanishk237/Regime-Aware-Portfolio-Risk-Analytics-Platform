import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.feature_builder import FeatureBuilder


def test_feature_builder_accepts_config_overrides_and_weights():
    dates = pd.date_range("2022-01-01", periods=100, freq="D")
    merged_df = pd.DataFrame(
        {
            "INFY.NS": [0.01 if i % 2 == 0 else -0.01 for i in range(100)],
            "RELIANCE.NS": [0.02 if i % 3 == 0 else -0.015 for i in range(100)],
            "vix": [15 + i * 0.1 for i in range(100)],
            "fii": [1000 - i * 10 for i in range(100)],
        },
        index=dates,
    )

    builder = FeatureBuilder(volatility_window=20)
    feature_matrix, metadata = builder.build(
        merged_df=merged_df,
        weights=[0.5, 0.5],
    )

    assert not feature_matrix.empty
    assert set(
        [
            "portfolio_return",
            "volatility_20",
            "drawdown",
            "vix",
            "fii",
        ]
    ).issubset(feature_matrix.columns)
    assert metadata["n_samples"] == len(feature_matrix)
    assert metadata["volatility_window"] == 20
