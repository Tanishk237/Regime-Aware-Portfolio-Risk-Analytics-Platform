import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.regime.predict_regime import RegimePredictor
from src.regime.train_hmm import HMMConfig, HMMTrainer


def build_feature_matrix() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=120, freq="D")
    rng = np.random.RandomState(42)

    returns = np.sin(np.arange(120) / 10.0) * 0.01 + rng.normal(0.0, 0.004, 120)
    volatility = np.abs(returns) * 5.0 + 0.1
    drawdown = np.abs(np.cumsum(returns)) * 0.2
    vix = 18 + np.sin(np.arange(120) / 15.0) * 6 + rng.normal(0.0, 0.5, 120)
    fii = 1000 + np.sin(np.arange(120) / 20.0) * 300 + rng.normal(0.0, 50, 120)
    dii = 700 + np.cos(np.arange(120) / 18.0) * 250 + rng.normal(0.0, 40, 120)
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


def test_regime_prediction_pipeline(tmp_path):
    feature_matrix = build_feature_matrix()
    model_dir = str(tmp_path / "models")
    trainer = HMMTrainer(HMMConfig(n_states=4, model_dir=model_dir))
    trainer.train(feature_matrix, save=True)

    predictor = RegimePredictor(model_dir=model_dir)
    payload = predictor.predict(feature_matrix)

    assert set(payload.keys()) == {"state_sequence", "current_state", "transition_matrix", "prediction_dataframe"}
    assert len(payload["state_sequence"]) == len(feature_matrix)
    assert payload["current_state"] in payload["prediction_dataframe"]["state"].tolist()
    assert payload["transition_matrix"].shape[0] == payload["transition_matrix"].shape[1]


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp_dir:
        test_regime_prediction_pipeline(Path(temp_dir))
    print("predict_regime test passed")
