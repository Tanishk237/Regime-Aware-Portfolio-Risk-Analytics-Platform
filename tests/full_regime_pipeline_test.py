import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.regime.predict_regime import RegimePredictor
from src.regime.probability_engine import RegimeProbabilityEngine
from src.regime.regime_summary import RegimeSummaryGenerator
from src.regime.state_labeller import StateLabeller
from src.regime.train_hmm import HMMConfig, HMMTrainer


def build_feature_matrix() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=140, freq="D")
    rng = np.random.RandomState(99)

    returns = np.sin(np.arange(140) / 8.0) * 0.015 + rng.normal(0.0, 0.005, 140)
    volatility = np.abs(returns) * 4.0 + 0.25
    drawdown = np.abs(np.cumsum(returns)) * 0.24
    vix = 14 + np.sin(np.arange(140) / 12.0) * 8 + rng.normal(0.0, 0.6, 140)
    fii = 950 + np.sin(np.arange(140) / 15.0) * 280 + rng.normal(0.0, 50, 140)
    dii = 700 + np.cos(np.arange(140) / 18.0) * 250 + rng.normal(0.0, 45, 140)
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


def test_full_regime_pipeline(tmp_path):
    feature_matrix = build_feature_matrix()
    model_dir = str(tmp_path / "models")
    trainer = HMMTrainer(HMMConfig(n_states=4, model_dir=model_dir))
    training_result = trainer.train(feature_matrix, save=True)

    predictor = RegimePredictor(model_dir=model_dir)
    prediction_payload = predictor.predict(feature_matrix)

    summary_generator = RegimeSummaryGenerator()
    summary_payload = summary_generator.generate_summary(feature_matrix, training_result["states"])

    labeller = StateLabeller(model_dir=model_dir)
    labels = labeller.generate_labels(feature_matrix, training_result["states"])
    labeller.save_labels(labels)

    probability_engine = RegimeProbabilityEngine(model_dir=model_dir)
    probability_df = probability_engine.probability_dataframe(feature_matrix)

    print("Current Regime:", prediction_payload["current_state"])
    print("Regime Distribution")
    print(training_result["states"].value_counts().sort_index())
    print("Transition Matrix")
    print(prediction_payload["transition_matrix"])
    print("Probability Table")
    print(probability_df.head())
    print("State Labels")
    print(labels)
    print("Summary Statistics")
    print(summary_payload["summary"])

    assert prediction_payload["prediction_dataframe"].shape[0] == len(feature_matrix)
    assert not summary_payload["summary"].empty
    assert not probability_df.empty
    assert set(labels.values()).issubset({"Bull", "Bear", "High Volatility", "Crisis"})


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp_dir:
        test_full_regime_pipeline(Path(temp_dir))
    print("full_regime_pipeline test passed")
