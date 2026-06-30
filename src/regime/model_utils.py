from pathlib import Path
import json
import joblib


class ModelUtils:
    """
    Utility class for saving and loading
    trained ML artifacts.
    """

    def __init__(
        self,
        model_dir="models"
    ):

        self.model_dir = Path(model_dir)

        self.model_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # -----------------------------------
    # Generic Save
    # -----------------------------------

    def save_pickle(
        self,
        obj,
        filename
    ):

        filepath = (
            self.model_dir /
            filename
        )

        joblib.dump(
            obj,
            filepath
        )

        return filepath

    # -----------------------------------
    # Generic Load
    # -----------------------------------

    def load_pickle(
        self,
        filename
    ):

        filepath = (
            self.model_dir /
            filename
        )

        return joblib.load(
            filepath
        )

    # -----------------------------------
    # Save JSON
    # -----------------------------------

    def save_json(
        self,
        data,
        filename
    ):

        filepath = (
            self.model_dir /
            filename
        )

        with open(
            filepath,
            "w"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

        return filepath

    # -----------------------------------
    # Load JSON
    # -----------------------------------

    def load_json(
        self,
        filename
    ):

        filepath = (
            self.model_dir /
            filename
        )

        with open(
            filepath,
            "r"
        ) as file:

            return json.load(
                file
            )

    # -----------------------------------
    # Save Complete Training Artifacts
    # -----------------------------------

    def save_training_artifacts(
        self,
        model,
        scaler,
        metadata,
        state_labels=None
    ):

        self.save_pickle(
            model,
            "hmm_model.pkl"
        )

        self.save_pickle(
            scaler,
            "scaler.pkl"
        )

        self.save_json(
            metadata,
            "training_metadata.json"
        )

        if state_labels is not None:

            self.save_json(
                state_labels,
                "state_labels.json"
            )

    # -----------------------------------
    # Load Everything
    # -----------------------------------

    def load_training_artifacts(
        self
    ):

        artifacts = {

            "model":
                self.load_pickle(
                    "hmm_model.pkl"
                ),

            "scaler":
                self.load_pickle(
                    "scaler.pkl"
                ),

            "metadata":
                self.load_json(
                    "training_metadata.json"
                )

        }

        state_file = (
            self.model_dir /
            "state_labels.json"
        )

        if state_file.exists():

            artifacts[
                "state_labels"
            ] = self.load_json(
                "state_labels.json"
            )

        return artifacts