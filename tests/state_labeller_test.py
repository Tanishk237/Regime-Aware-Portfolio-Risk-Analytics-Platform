import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.regime.state_labeller import StateLabeller
from src.regime.train_hmm import HMMConfig, HMMTrainer


def build_feature_matrix() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=120, freq="D")
    rng = np.random.RandomState(7)

    returns = np.sin(np.arange(120) / 12.0) * 0.01 + rng.normal(0.0, 0.004, 120)
    volatility = np.abs(returns) * 5.0 + 0.3
    drawdown = np.abs(np.cumsum(returns)) * 0.25
    vix = 16 + np.sin(np.arange(120) / 20.0) * 7 + rng.normal(0.0, 0.6, 120)
    fii = 800 + np.sin(np.arange(120) / 16.0) * 250 + rng.normal(0.0, 40, 120)
    dii = 600 + np.cos(np.arange(120) / 18.0) * 230 + rng.normal(0.0, 35, 120)
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


def test_state_labelling_pipeline():
    feature_matrix = build_feature_matrix()
    trainer = HMMTrainer(HMMConfig(n_states=4, model_dir="models"))
    training_result = trainer.train(feature_matrix, save=True)

    labeller = StateLabeller(model_dir="models")
    labels = labeller.generate_labels(feature_matrix, training_result["states"])
    labeller.save_labels(labels)
    loaded_labels = labeller.load_labels()
    labelled_predictions = labeller.label_predictions(training_result["states"])

    assert set(labels.values()).issubset({"Bull", "Bear", "High Volatility", "Crisis"})
    assert loaded_labels == labels
    assert len(labelled_predictions) == len(training_result["states"])


if __name__ == "__main__":
    test_state_labelling_pipeline()
    print("state_labeller test passed")
