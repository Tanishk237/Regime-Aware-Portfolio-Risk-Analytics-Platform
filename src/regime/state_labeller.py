"""Infer human-readable labels for hidden states."""

from __future__ import annotations

import pandas as pd

from src.regime.model_utils import ModelUtils
from src.regime.regime_summary import RegimeSummaryGenerator


class StateLabeller:
    """Generate, save, load and apply state labels."""

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.model_utils = ModelUtils(model_dir=model_dir)
        self.state_labels: dict[int, str] = {}
        self.summary_generator = RegimeSummaryGenerator()

    def generate_labels(self, feature_matrix: pd.DataFrame, predictions) -> dict[int, str]:
        """Infer labels from the state-level regime statistics."""
        summary_payload = self.summary_generator.generate_summary(feature_matrix, predictions)
        summary_df = summary_payload["summary"]

        labels: dict[int, str] = {}
        if summary_df.empty:
            return labels

        return_threshold = summary_df["average_return"].quantile(0.5)
        volatility_threshold = summary_df["average_volatility"].quantile(0.75)
        drawdown_threshold = summary_df["average_drawdown"].quantile(0.75)
        vix_threshold = summary_df["average_vix"].quantile(0.75)

        for _, row in summary_df.iterrows():
            state_id = int(row["state"])
            avg_return = float(row["average_return"])
            avg_volatility = float(row["average_volatility"])
            avg_drawdown = float(row["average_drawdown"])
            avg_vix = float(row["average_vix"])

            if avg_drawdown >= drawdown_threshold and avg_return <= return_threshold:
                label = "Crisis"
            elif avg_volatility >= volatility_threshold or avg_vix >= vix_threshold:
                label = "High Volatility"
            elif avg_return > return_threshold:
                label = "Bull"
            else:
                label = "Bear"

            labels[state_id] = label

        self.state_labels = labels
        return labels

    def save_labels(self, labels: dict[int, str] | None = None) -> None:
        """Persist the state labels to the model directory."""
        labels_to_save = labels or self.state_labels
        if not labels_to_save:
            raise ValueError("No labels available to save")
        normalized_labels = {int(key): value for key, value in labels_to_save.items()}
        self.model_utils.save_json(normalized_labels, "state_labels.json")

    def load_labels(self) -> dict[int, str]:
        """Load a previous state label mapping if present."""
        try:
            raw_labels = self.model_utils.load_json("state_labels.json")
            self.state_labels = {int(key): value for key, value in raw_labels.items()}
        except FileNotFoundError:
            self.state_labels = {}
        return self.state_labels

    def label_predictions(self, predictions) -> pd.Series:
        """Convert predicted state ids to readable regime labels."""
        if not self.state_labels:
            self.load_labels()

        if not self.state_labels:
            raise ValueError("No state labels are available. Generate labels first.")

        state_sequence = pd.Series(predictions, dtype=int)
        return state_sequence.map(lambda state: self.state_labels.get(int(state), f"state_{state}"))
