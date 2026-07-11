"""Utilities for predicting market regimes from a feature matrix."""

from __future__ import annotations

import pandas as pd

from src.regime.model_utils import ModelUtils


class RegimePredictor:
    """Load a trained HMM and expose a simple prediction interface."""

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
                "Training artifacts were not found. Train the HMM before predicting regimes."
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

    def predict_states(self, feature_matrix: pd.DataFrame) -> pd.Series:
        """Return the predicted state id for each observation."""
        feature_matrix = self._validate_feature_matrix(feature_matrix)
        scaled_features = self._scale_features(feature_matrix)
        predicted_states = self.model.predict(scaled_features.values)
        return pd.Series(predicted_states, index=feature_matrix.index, name="state")

    def predict_current_state(self, feature_matrix: pd.DataFrame) -> int:
        """Return the most recent predicted state."""
        state_sequence = self.predict_states(feature_matrix)
        return int(state_sequence.iloc[-1])

    def transition_matrix(self) -> pd.DataFrame:
        """Return the learned transition matrix as a DataFrame."""
        transition_matrix = getattr(self.model, "transmat_", None)
        if transition_matrix is None:
            raise AttributeError("The loaded model does not expose a transition matrix")

        state_ids = list(range(transition_matrix.shape[0]))
        return pd.DataFrame(transition_matrix, index=state_ids, columns=state_ids)

    def build_prediction_dataframe(self, feature_matrix: pd.DataFrame) -> pd.DataFrame:
        """Build a DataFrame with the predicted state and its label."""
        state_sequence = self.predict_states(feature_matrix)
        state_labels = []
        for state in state_sequence:
            state_labels.append(self.state_labels.get(int(state), f"state_{state}"))

        return pd.DataFrame(
            {
                "state": state_sequence.astype(int),
                "state_label": state_labels,
            },
            index=state_sequence.index,
        )

    def predict(self, feature_matrix: pd.DataFrame) -> dict:
        """Predict regimes and return the requested structured payload."""
        prediction_df = self.build_prediction_dataframe(feature_matrix)
        return {
            "state_sequence": prediction_df["state"],
            "current_state": int(prediction_df["state"].iloc[-1]),
            "transition_matrix": self.transition_matrix(),
            "prediction_dataframe": prediction_df,
        }
