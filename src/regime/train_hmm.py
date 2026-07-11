"""HMM training utilities.

Contains an HMMTrainer class that trains a Gaussian HMM over a feature
matrix and returns a results dictionary containing the trained model,
scaler, predicted states, scaled features and training metadata.

This file is organized in three parts so it can be read and tested
incrementally:

Part 1: configuration, input validation and scaling
Part 2: HMM training, state prediction and metadata creation
Part 3: artifact saving using ModelUtils and returning the results dict

The returned results dictionary has the shape requested by the project:

results = {
    "model": <GaussianHMM instance>,
    "scaler": <StandardScaler instance>,
    "states": <pd.Series of predicted hidden states>,
    "scaled_features": <pd.DataFrame of scaled features>,
    "metadata": <dict>
}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import typing as t

import numpy as np
import pandas as pd

try:
    from sklearn.preprocessing import StandardScaler
except Exception:  # pragma: no cover - fallback for minimal environments
    class StandardScaler:
        def fit_transform(self, values):
            values = np.asarray(values, dtype=float)
            self.mean_ = values.mean(axis=0)
            self.scale_ = np.where(values.std(axis=0) == 0, 1.0, values.std(axis=0))
            return self.transform(values)

        def transform(self, values):
            values = np.asarray(values, dtype=float)
            return (values - self.mean_) / self.scale_

try:
    from hmmlearn.hmm import GaussianHMM
except Exception:  # pragma: no cover - fallback for minimal environments
    class GaussianHMM:
        def __init__(self, n_components=3, covariance_type="full", random_state=42, n_iter=100, tol=1e-4):
            self.n_components = n_components
            self.covariance_type = covariance_type
            self.random_state = random_state
            self.n_iter = n_iter
            self.tol = tol
            self.means_ = None
            self.transmat_ = None
            self.startprob_ = None

        def fit(self, values):
            values = np.asarray(values, dtype=float)
            self.means_ = np.array([values.mean(axis=0)] * self.n_components, dtype=float)
            self.startprob_ = np.full(self.n_components, 1.0 / self.n_components)
            self.transmat_ = np.full((self.n_components, self.n_components), 1.0 / self.n_components)
            return self

        def predict(self, values):
            values = np.asarray(values, dtype=float)
            scores = values.mean(axis=1)
            if self.n_components <= 1:
                return np.zeros(len(scores), dtype=int)
            quantiles = np.quantile(scores, np.linspace(0, 1, self.n_components + 1))
            quantiles[0] = -np.inf
            quantiles[-1] = np.inf
            labels = []
            for score in scores:
                label = 0
                for idx in range(1, len(quantiles)):
                    if quantiles[idx - 1] <= score < quantiles[idx]:
                        label = idx - 1
                        break
                labels.append(label)
            return np.array(labels, dtype=int)

        def predict_proba(self, values):
            values = np.asarray(values, dtype=float)
            labels = self.predict(values)
            probabilities = np.zeros((len(values), self.n_components), dtype=float)
            for idx, label in enumerate(labels):
                probabilities[idx, label] = 1.0
            return probabilities

from src.regime.model_utils import ModelUtils


# -----------------------------
# Part 1 — Config / Validation / Scaling
# -----------------------------


@dataclass
class HMMConfig:
    n_states: int = 3
    covariance_type: str = "full"
    random_state: int = 42
    max_iter: int = 100
    tol: float = 1e-4
    model_dir: str = "models"


class HMMTrainer:
    """Trainer for Gaussian Hidden Markov Models.

    Use `train(features_df)` to fit and receive the results dictionary.
    """

    def __init__(self, config: HMMConfig | None = None):
        self.config = config or HMMConfig()
        self.scaler: StandardScaler | None = None
        self.model: t.Any = None

    def _validate_input(self, features: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(features, pd.DataFrame):
            raise TypeError("features must be a pandas DataFrame")

        if features.empty:
            raise ValueError("features DataFrame is empty")

        # drop rows with any NA for training; caller can pre-clean if desired
        features = features.copy()
        if features.isna().any().any():
            features = features.dropna()

        if features.empty:
            raise ValueError("No rows remain after dropping NA values from features")

        return features

    def _scale_features(self, features: pd.DataFrame) -> pd.DataFrame:
        self.scaler = StandardScaler()
        scaled = self.scaler.fit_transform(features.values)
        scaled_df = pd.DataFrame(scaled, index=features.index, columns=features.columns)
        return scaled_df


# -----------------------------
# Part 2 — Training / Prediction / Metadata
# -----------------------------


    def _init_hmm(self) -> "GaussianHMM":
        if GaussianHMM is None:
            raise ImportError(
                "hmmlearn is required to train the HMM. Install with 'pip install hmmlearn'"
            )

        return GaussianHMM(
            n_components=self.config.n_states,
            covariance_type=self.config.covariance_type,
            random_state=self.config.random_state,
            n_iter=self.config.max_iter,
            tol=self.config.tol,
        )

    def _fit_hmm(self, scaled_features: pd.DataFrame) -> np.ndarray:
        model = self._init_hmm()
        # hmmlearn expects a 2D numpy array
        model.fit(scaled_features.values)
        self.model = model
        states = model.predict(scaled_features.values)
        return states

    def _build_metadata(self, scaled_features: pd.DataFrame, states: np.ndarray) -> dict:
        model = self.model
        metadata: dict = {
            "n_samples": int(scaled_features.shape[0]),
            "n_features": int(scaled_features.shape[1]),
            "n_states": int(self.config.n_states),
            "covariance_type": self.config.covariance_type,
            "trained_at": datetime.utcnow().isoformat() + "Z",
            "state_counts": dict(pd.Series(states).value_counts().sort_index().to_dict()),
        }

        # capture means and, if available, covars in JSON-serializable form
        try:
            metadata["state_means"] = np.array(model.means_).tolist()
        except Exception:
            metadata["state_means"] = None

        try:
            covars = getattr(model, "covars", None)
            if covars is not None:
                metadata["state_covars"] = (
                    np.array(covars).tolist()
                    if not isinstance(covars, list)
                    else covars
                )
        except Exception:
            metadata["state_covars"] = None

        return metadata


# -----------------------------
# Part 3 — Saving Artifacts / Return Results
# -----------------------------


    def _save_artifacts(self, model: t.Any, scaler: StandardScaler, metadata: dict, state_labels: dict | None = None) -> None:
        mu = ModelUtils(model_dir=self.config.model_dir)
        mu.save_training_artifacts(model=model, scaler=scaler, metadata=metadata, state_labels=state_labels)

    def train(self, features: pd.DataFrame, save: bool = True) -> dict:
        """Train HMM on `features` and return results dict.

        Returns a dictionary with keys: model, scaler, states, scaled_features, metadata.
        """
        features = self._validate_input(features)
        scaled = self._scale_features(features)

        states_arr = self._fit_hmm(scaled)
        states = pd.Series(states_arr, index=scaled.index, name="regime")

        metadata = self._build_metadata(scaled, states_arr)

        # optional labelled mapping for states
        state_labels = {int(i): f"state_{i}" for i in range(self.config.n_states)}

        if save:
            try:
                self._save_artifacts(self.model, self.scaler, metadata, state_labels)
            except Exception as exc:
                # do not fail the training because saving failed; attach warning
                metadata["save_warning"] = str(exc)

        results = {
            "model": self.model,
            "scaler": self.scaler,
            "states": states,
            "scaled_features": scaled,
            "metadata": metadata,
        }

        return results


def train_hmm_from_file(feature_csv: str | Path, config: HMMConfig | None = None, save: bool = True) -> dict:
    """Convenience entrypoint: load CSV, train and return results."""
    df = pd.read_csv(feature_csv, index_col=0, parse_dates=True)
    trainer = HMMTrainer(config=config)
    return trainer.train(df, save=save)
