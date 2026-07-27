import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.regime.regime_summary import RegimeSummaryGenerator


def test_regime_duration_stats_use_consecutive_runs():
    feature_matrix = pd.DataFrame(
        {
            "portfolio_return": [0.01, 0.02, -0.01, -0.02, 0.03, 0.01],
            "volatility_20": [0.1, 0.2, 0.4, 0.5, 0.2, 0.1],
            "drawdown": [0.0, 0.0, -0.1, -0.2, -0.05, 0.0],
            "vix": [12, 13, 22, 23, 14, 15],
        }
    )
    predictions = pd.Series([0, 0, 1, 1, 0, 0])

    result = RegimeSummaryGenerator().generate_summary(
        feature_matrix,
        predictions
    )

    duration_stats = result["duration_stats"].set_index("state")

    assert duration_stats.loc[0, "mean_duration"] == 2.0
    assert duration_stats.loc[0, "max_duration"] == 2
    assert duration_stats.loc[1, "mean_duration"] == 2.0
    assert duration_stats.loc[1, "min_duration"] == 2
