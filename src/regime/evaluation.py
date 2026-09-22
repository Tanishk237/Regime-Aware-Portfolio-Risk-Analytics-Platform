from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score


REQUIRED_COLUMNS = {
    "date",
    "training_end_date",
    "actual_regime",
    "predicted_regime",
    "probability",
}


def evaluate_walk_forward_predictions(
    records: pd.DataFrame,
    *,
    fold_size: int = 30,
    minimum_samples: int = 120,
    minimum_folds: int = 3,
    minimum_balanced_accuracy: float = 0.55,
) -> dict[str, Any]:
    missing = REQUIRED_COLUMNS.difference(records.columns)
    if missing:
        raise ValueError("Missing evaluation columns: " + ", ".join(sorted(missing)))
    if fold_size < 1:
        raise ValueError("fold_size must be positive")

    frame = records.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise", utc=True)
    frame["training_end_date"] = pd.to_datetime(
        frame["training_end_date"], errors="raise", utc=True
    )
    frame["probability"] = pd.to_numeric(frame["probability"], errors="raise")
    frame = frame.sort_values("date").drop_duplicates("date", keep="last")
    if frame.empty:
        raise ValueError("Evaluation dataset is empty")
    if (frame["training_end_date"] >= frame["date"]).any():
        raise ValueError(
            "Walk-forward leakage detected: every training_end_date must precede its prediction date"
        )
    if ((frame["probability"] < 0) | (frame["probability"] > 1)).any():
        raise ValueError("probability values must be between 0 and 1")

    actual = frame["actual_regime"].astype(str)
    predicted = frame["predicted_regime"].astype(str)
    labels = sorted(set(actual).union(predicted))
    correct = (actual == predicted).astype(float)
    confidence = frame["probability"].astype(float)
    brier_correctness = float(np.mean((confidence - correct) ** 2))

    folds = []
    for fold_index, start in enumerate(range(0, len(frame), fold_size), start=1):
        fold = frame.iloc[start : start + fold_size]
        if fold.empty:
            continue
        fold_actual = fold["actual_regime"].astype(str)
        fold_predicted = fold["predicted_regime"].astype(str)
        folds.append(
            {
                "fold": fold_index,
                "start_date": fold["date"].iloc[0].date().isoformat(),
                "end_date": fold["date"].iloc[-1].date().isoformat(),
                "samples": len(fold),
                "accuracy": float(accuracy_score(fold_actual, fold_predicted)),
                "balanced_accuracy": float(
                    balanced_accuracy_score(fold_actual, fold_predicted)
                ),
                "macro_f1": float(
                    f1_score(fold_actual, fold_predicted, average="macro", zero_division=0)
                ),
            }
        )

    metrics = {
        "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, average="macro", zero_division=0)),
        "brier_correctness": brier_correctness,
    }
    gate_checks = {
        "minimum_samples": len(frame) >= minimum_samples,
        "minimum_folds": len(folds) >= minimum_folds,
        "minimum_balanced_accuracy": metrics["balanced_accuracy"] >= minimum_balanced_accuracy,
        "no_time_leakage": True,
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validated": all(gate_checks.values()),
        "scope": "time-ordered out-of-sample regime classification",
        "samples": len(frame),
        "labels": labels,
        "metrics": metrics,
        "confusion_matrix": {
            "labels": labels,
            "values": confusion_matrix(actual, predicted, labels=labels).tolist(),
        },
        "folds": folds,
        "gate": {
            "checks": gate_checks,
            "minimum_samples": minimum_samples,
            "minimum_folds": minimum_folds,
            "minimum_balanced_accuracy": minimum_balanced_accuracy,
        },
        "disclosure": (
            "This report measures classification against supplied independent labels. "
            "It does not guarantee future returns or market-direction forecasts."
        ),
    }
