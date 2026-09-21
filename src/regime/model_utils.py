from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import hmmlearn
import joblib
import sklearn


ARTIFACT_SCHEMA_VERSION = 1


class ModelArtifactError(RuntimeError):
    """Raised when persisted model artifacts are incomplete or incompatible."""


class ModelUtils:
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def save_pickle(self, obj: Any, filename: str) -> Path:
        filepath = self.model_dir / filename
        temporary = filepath.with_suffix(f"{filepath.suffix}.tmp")
        joblib.dump(obj, temporary)
        temporary.replace(filepath)
        return filepath

    def load_pickle(self, filename: str) -> Any:
        return joblib.load(self.model_dir / filename)

    def save_json(self, data: dict, filename: str) -> Path:
        filepath = self.model_dir / filename
        temporary = filepath.with_suffix(f"{filepath.suffix}.tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temporary.replace(filepath)
        return filepath

    def load_json(self, filename: str) -> dict:
        return json.loads((self.model_dir / filename).read_text(encoding="utf-8"))

    def save_training_artifacts(
        self,
        model: Any,
        scaler: Any,
        metadata: dict,
        state_labels: dict | None = None,
    ) -> None:
        self.save_pickle(model, "hmm_model.pkl")
        self.save_pickle(scaler, "scaler.pkl")
        self.save_json(metadata, "training_metadata.json")
        if state_labels is not None:
            self.save_json(state_labels, "state_labels.json")

    def load_training_artifacts(self) -> dict[str, Any]:
        # Metadata is checked before unpickling version-sensitive objects.
        metadata = self.load_json("training_metadata.json")
        self._validate_metadata(metadata)
        artifacts: dict[str, Any] = {
            "model": self.load_pickle("hmm_model.pkl"),
            "scaler": self.load_pickle("scaler.pkl"),
            "metadata": metadata,
        }
        state_file = self.model_dir / "state_labels.json"
        if state_file.exists():
            artifacts["state_labels"] = self.load_json("state_labels.json")
        return artifacts

    @staticmethod
    def _validate_metadata(metadata: dict) -> None:
        if metadata.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION:
            raise ModelArtifactError(
                "HMM artifacts use an unsupported schema. Retrain the model with this release."
            )
        versions = metadata.get("library_versions", {})
        expected = {
            "scikit_learn": sklearn.__version__,
            "hmmlearn": hmmlearn.__version__,
        }
        mismatches = [
            name
            for name, current in expected.items()
            if versions.get(name) != current
        ]
        if mismatches:
            raise ModelArtifactError(
                "HMM artifacts were built with incompatible libraries: "
                + ", ".join(mismatches)
            )
