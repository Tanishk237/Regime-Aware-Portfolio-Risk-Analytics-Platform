"""Calculate posterior regime probabilities from a trained HMM."""

from __future__ import annotations

import pandas as pd

from src.regime.model_utils import ModelUtils


class RegimeProbabilityEngine:
    """Return posterior probabilities for each hidden state."""

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.model_utils = ModelUtils(model_dir=model_dir)
        self.model = None
        self.scaler = None
        self.state_labels = {}
        self._load_artifacts()

    def _load_artifacts(self) -> None:
        artifacts = self.model_utils.load_training_artifacts()
        self.model = artifacts.get("model")
        self.scaler = artifacts.get("scaler")
        raw_state_labels = artifacts.get("state_labels", {})
        self.state_labels = {int(key): value for key, value in raw_state_labels.items()}

        if self.model is None or self.scaler is None:
            raise FileNotFoundError(
                "Training artifacts were not found. Train the HMM before calculating probabilities."
            )

    @staticmethod
    def _validate_feature_matrix(feature_matrix: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(feature_matrix, pd.DataFrame):
            raise TypeError("feature_matrix must be a pandas DataFrame")

        if feature_matrix.empty:
            raise ValueError("feature_matrix cannot be empty")

        return feature_matrix.copy()

    def _scale_features(self, feature_matrix: pd.DataFrame) -> pd.DataFrame:
        scaled_values = self.scaler.transform(feature_matrix.values)
        return pd.DataFrame(
            scaled_values,
            index=feature_matrix.index,
            columns=feature_matrix.columns,
        )

    def probability_dataframe(self, feature_matrix: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame containing posterior probabilities for each state."""
        feature_matrix = self._validate_feature_matrix(feature_matrix)
        scaled_features = self._scale_features(feature_matrix)
        probabilities = self.model.predict_proba(scaled_features.values)

        state_ids = list(range(probabilities.shape[1]))
        columns = [self.state_labels.get(state_id, f"state_{state_id}") for state_id in state_ids]
        return pd.DataFrame(probabilities, index=feature_matrix.index, columns=columns)

    def current_probabilities(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """Return the most recent row of posterior probabilities."""
        probability_df = self.probability_dataframe(feature_matrix)
        return probability_df.iloc[-1]

    def most_probable_regime(self, feature_matrix: pd.DataFrame) -> tuple[str, float]:
        """Return the most probable regime and its posterior probability."""
        current_probabilities = self.current_probabilities(feature_matrix)
        regime = current_probabilities.idxmax()
        probability = float(current_probabilities.max())
        return regime, probability
