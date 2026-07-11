import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.regime.probability_engine import RegimeProbabilityEngine
from src.regime.train_hmm import HMMConfig, HMMTrainer


def build_feature_matrix() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=120, freq="D")
    rng = np.random.RandomState(11)

    returns = np.sin(np.arange(120) / 14.0) * 0.012 + rng.normal(0.0, 0.003, 120)
    volatility = np.abs(returns) * 4.5 + 0.2
    drawdown = np.abs(np.cumsum(returns)) * 0.18
    vix = 15 + np.sin(np.arange(120) / 17.0) * 5 + rng.normal(0.0, 0.4, 120)
    fii = 900 + np.sin(np.arange(120) / 19.0) * 260 + rng.normal(0.0, 45, 120)
    dii = 650 + np.cos(np.arange(120) / 20.0) * 220 + rng.normal(0.0, 38, 120)
    net_flow = fii - dii

    return pd.DataFrame(
        {
            "portfolio_return": returns,
            "volatility_20": volatility,
            "drawdown": drawdown,
            "vix": vix,
            "fii": fii,
            "dii": dii,
            "net_flow": net_flow,
        },
        index=dates,
    )


def test_probability_engine():
    feature_matrix = build_feature_matrix()
    trainer = HMMTrainer(HMMConfig(n_states=4, model_dir="models"))
    trainer.train(feature_matrix, save=True)

    engine = RegimeProbabilityEngine(model_dir="models")
    probability_df = engine.probability_dataframe(feature_matrix)
    current_probabilities = engine.current_probabilities(feature_matrix)
    most_probable_regime = engine.most_probable_regime(feature_matrix)

    assert probability_df.shape[0] == len(feature_matrix)
    assert probability_df.shape[1] >= 2
    assert current_probabilities.sum() > 0.0
    assert isinstance(most_probable_regime[0], str)


if __name__ == "__main__":
    test_probability_engine()
    print("probability_engine test passed")
