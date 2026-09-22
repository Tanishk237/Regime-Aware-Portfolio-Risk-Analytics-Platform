from __future__ import annotations

import pandas as pd
import pytest

from src.regime.evaluation import evaluate_walk_forward_predictions


def evaluation_rows(samples: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2025-01-02", periods=samples, freq="D", tz="UTC")
    labels = ["Bull", "Bear", "Crisis", "High Volatility"]
    actual = [labels[index % len(labels)] for index in range(samples)]
    predicted = [
        label if index % 5 else labels[(labels.index(label) + 1) % len(labels)]
        for index, label in enumerate(actual)
    ]
    return pd.DataFrame(
        {
            "date": dates,
            "training_end_date": dates - pd.Timedelta(days=1),
            "actual_regime": actual,
            "predicted_regime": predicted,
            "probability": [0.75 if left == right else 0.55 for left, right in zip(actual, predicted)],
        }
    )


def test_walk_forward_evaluation_builds_release_gate_report():
    report = evaluate_walk_forward_predictions(evaluation_rows())

    assert report["validated"] is True
    assert report["samples"] == 120
    assert len(report["folds"]) == 4
    assert report["metrics"]["balanced_accuracy"] >= 0.55
    assert report["gate"]["checks"]["no_time_leakage"] is True
    assert report["confusion_matrix"]["labels"] == [
        "Bear",
        "Bull",
        "Crisis",
        "High Volatility",
    ]


def test_walk_forward_evaluation_rejects_training_leakage():
    rows = evaluation_rows(8)
    rows.loc[0, "training_end_date"] = rows.loc[0, "date"]

    with pytest.raises(ValueError, match="leakage"):
        evaluate_walk_forward_predictions(rows, minimum_samples=1, minimum_folds=1)
