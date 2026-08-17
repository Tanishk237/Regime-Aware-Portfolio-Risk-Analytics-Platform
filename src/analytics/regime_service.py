from __future__ import annotations

import pandas as pd

from src.regime.predict_regime import RegimePredictor
from src.regime.probability_engine import RegimeProbabilityEngine


class AnalyticsRegimeService:
    def _predict_regimes(self, feature_matrix: pd.DataFrame) -> dict:
        try:
            predictor = RegimePredictor(model_dir=self.model_dir)
            probabilities = RegimeProbabilityEngine(model_dir=self.model_dir).probability_dataframe(feature_matrix)
            prediction_df = predictor.build_prediction_dataframe(feature_matrix)
            transition_matrix = predictor.transition_matrix()
            state_labels = predictor.state_labels
        except Exception:
            prediction_df, probabilities, transition_matrix, state_labels = self._fallback_regime_prediction(feature_matrix)

        history = []
        for row_date, row in prediction_df.iterrows():
            state = int(row["state"])
            label = str(row["state_label"])
            probability = float(probabilities.loc[row_date].max())
            history.append(
                {
                    "date": self._to_date(row_date),
                    "hidden_state": state,
                    "regime_label": label,
                    "probability": probability,
                }
            )

        current = history[-1]
        return {
            "current_regime": current["regime_label"],
            "current_state": current["hidden_state"],
            "regime_probability": current["probability"],
            "history": history,
            "transition_matrix": self._dataframe_to_matrix(transition_matrix),
            "statistics": self._regime_statistics(feature_matrix, prediction_df),
            "duration": self._regime_duration(prediction_df["state"]),
            "state_labels": {str(key): value for key, value in state_labels.items()},
        }

    def _fallback_regime_prediction(self, feature_matrix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[int, str]]:
        volatility_column = "volatility_20" if "volatility_20" in feature_matrix.columns else None
        return_column = "portfolio_return" if "portfolio_return" in feature_matrix.columns else None
        vix_column = "vix" if "vix" in feature_matrix.columns else None
        volatility_threshold = feature_matrix[volatility_column].quantile(0.75) if volatility_column else None
        return_threshold = feature_matrix[return_column].quantile(0.4) if return_column else None
        vix_threshold = feature_matrix[vix_column].quantile(0.75) if vix_column else None

        states = []
        labels = []
        for _, row in feature_matrix.iterrows():
            if volatility_column and row[volatility_column] >= volatility_threshold:
                state, label = 2, "High Volatility"
            elif vix_column and row[vix_column] >= vix_threshold:
                state, label = 2, "High Volatility"
            elif return_column and row[return_column] < return_threshold:
                state, label = 1, "Bear"
            else:
                state, label = 0, "Bull"
            states.append(state)
            labels.append(label)

        prediction_df = pd.DataFrame(
            {"state": states, "state_label": labels},
            index=feature_matrix.index,
        )
        state_labels = {0: "Bull", 1: "Bear", 2: "High Volatility"}
        probabilities = pd.DataFrame(0.05, index=feature_matrix.index, columns=list(state_labels.values()))
        for row_date, label in zip(feature_matrix.index, labels):
            probabilities.loc[row_date, label] = 0.90

        transition_matrix = self._estimate_transition_matrix(pd.Series(states), state_count=3)
        return prediction_df, probabilities, transition_matrix, state_labels

    def _regime_statistics(self, feature_matrix: pd.DataFrame, prediction_df: pd.DataFrame) -> list[dict]:
        frame = feature_matrix.copy()
        frame["hidden_state"] = prediction_df["state"].astype(int)
        frame["regime_label"] = prediction_df["state_label"]
        rows = []
        for (state, label), group in frame.groupby(["hidden_state", "regime_label"]):
            rows.append(
                {
                    "hidden_state": int(state),
                    "regime_label": str(label),
                    "sample_count": int(len(group)),
                    "average_return": self._optional_float(group.get("portfolio_return", pd.Series(dtype=float)).mean()),
                    "average_volatility": self._optional_float(group.get("volatility_20", pd.Series(dtype=float)).mean()),
                    "average_drawdown": self._optional_float(group.get("drawdown", pd.Series(dtype=float)).mean()),
                    "average_vix": self._optional_float(group.get("vix", pd.Series(dtype=float)).mean()),
                }
            )
        return rows

    def _regime_duration(self, states: pd.Series) -> list[dict]:
        rows = []
        previous_state = None
        start = None
        duration = 0
        previous_date = None
        for row_date, state in states.items():
            state = int(state)
            if previous_state is None:
                previous_state = state
                start = row_date
                duration = 1
                previous_date = row_date
                continue
            if state == previous_state:
                duration += 1
                previous_date = row_date
                continue
            rows.append(
                {
                    "hidden_state": int(previous_state),
                    "start_date": self._to_date(start),
                    "end_date": self._to_date(previous_date),
                    "duration_days": duration,
                }
            )
            previous_state = state
            start = row_date
            duration = 1
            previous_date = row_date
        if previous_state is not None:
            rows.append(
                {
                    "hidden_state": int(previous_state),
                    "start_date": self._to_date(start),
                    "end_date": self._to_date(states.index[-1]),
                    "duration_days": duration,
                }
            )
        return rows
