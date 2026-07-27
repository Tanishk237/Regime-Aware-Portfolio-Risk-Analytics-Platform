"""Generate descriptive regime summary statistics."""

from __future__ import annotations

import pandas as pd


class RegimeSummaryGenerator:
    """Generate summary statistics for each hidden state."""

    def __init__(self) -> None:
        self._metric_lookup = {
            "return": ["portfolio_return", "return"],
            "volatility": ["volatility", "volatility_20"],
            "drawdown": ["drawdown"],
            "vix": ["vix"],
            "fii": ["fii"],
            "dii": ["dii"],
            "net_flow": ["net_flow"],
        }

    @staticmethod
    def _coerce_states(predictions: pd.Series | pd.DataFrame | list | tuple) -> pd.Series:
        if isinstance(predictions, pd.Series):
            return predictions.astype(int)

        if isinstance(predictions, pd.DataFrame):
            if predictions.shape[1] != 1:
                raise ValueError("predictions DataFrame must contain a single state column")
            return predictions.iloc[:, 0].astype(int)

        return pd.Series(list(predictions), dtype=int)

    def _resolve_metric_column(self, feature_matrix: pd.DataFrame, metric_name: str) -> str | None:
        candidates = self._metric_lookup.get(metric_name, [])
        normalized_columns = {column.lower(): column for column in feature_matrix.columns}

        for candidate in candidates:
            if candidate.lower() in normalized_columns:
                return normalized_columns[candidate.lower()]

        for column in feature_matrix.columns:
            lowered = column.lower()
            if metric_name.lower() in lowered:
                return column

        return None

    @staticmethod
    def _regime_durations_by_state(state_sequence: pd.Series) -> dict[int, list[int]]:
        durations_by_state: dict[int, list[int]] = {}
        current_duration = 1
        previous_state = None

        for state in state_sequence.tolist():
            state = int(state)

            if previous_state is None:
                previous_state = state
                continue

            if state == previous_state:
                current_duration += 1
            else:
                durations_by_state.setdefault(
                    int(previous_state),
                    []
                ).append(current_duration)
                current_duration = 1
                previous_state = state

        if previous_state is not None:
            durations_by_state.setdefault(
                int(previous_state),
                []
            ).append(current_duration)

        return durations_by_state

    def generate_summary(
        self,
        feature_matrix: pd.DataFrame,
        predictions: pd.Series | pd.DataFrame | list | tuple,
    ) -> dict[str, pd.DataFrame]:
        """Return summary statistics and duration statistics per state."""
        feature_matrix = feature_matrix.copy()
        state_sequence = self._coerce_states(predictions)

        if len(state_sequence) != len(feature_matrix):
            raise ValueError("predictions and feature_matrix must have the same length")

        feature_matrix = feature_matrix.set_index(state_sequence.index)
        feature_matrix["state"] = state_sequence.astype(int)

        summary_rows: list[dict] = []
        duration_rows: list[dict] = []
        durations_by_state = self._regime_durations_by_state(
            state_sequence
        )

        for state in sorted(feature_matrix["state"].unique().tolist()):
            state_slice = feature_matrix.loc[feature_matrix["state"] == state]
            durations = durations_by_state.get(
                int(state),
                []
            )

            summary_rows.append(
                {
                    "state": int(state),
                    "sample_count": int(len(state_slice)),
                    "average_return": float(state_slice[self._resolve_metric_column(feature_matrix, "return")].mean()) if self._resolve_metric_column(feature_matrix, "return") else float("nan"),
                    "average_volatility": float(state_slice[self._resolve_metric_column(feature_matrix, "volatility")].mean()) if self._resolve_metric_column(feature_matrix, "volatility") else float("nan"),
                    "average_drawdown": float(state_slice[self._resolve_metric_column(feature_matrix, "drawdown")].mean()) if self._resolve_metric_column(feature_matrix, "drawdown") else float("nan"),
                    "average_vix": float(state_slice[self._resolve_metric_column(feature_matrix, "vix")].mean()) if self._resolve_metric_column(feature_matrix, "vix") else float("nan"),
                    "average_fii": float(state_slice[self._resolve_metric_column(feature_matrix, "fii")].mean()) if self._resolve_metric_column(feature_matrix, "fii") else float("nan"),
                    "average_dii": float(state_slice[self._resolve_metric_column(feature_matrix, "dii")].mean()) if self._resolve_metric_column(feature_matrix, "dii") else float("nan"),
                    "average_net_flow": float(state_slice[self._resolve_metric_column(feature_matrix, "net_flow")].mean()) if self._resolve_metric_column(feature_matrix, "net_flow") else float("nan"),
                    "first_occurrence": state_slice.index[0],
                    "last_occurrence": state_slice.index[-1],
                }
            )

            if durations:
                duration_rows.append(
                    {
                        "state": int(state),
                        "mean_duration": float(pd.Series(durations).mean()),
                        "median_duration": float(pd.Series(durations).median()),
                        "max_duration": int(pd.Series(durations).max()),
                        "min_duration": int(pd.Series(durations).min()),
                    }
                )

        summary_df = pd.DataFrame(summary_rows)
        duration_df = pd.DataFrame(duration_rows)

        if not summary_df.empty and "state" in summary_df.columns:
            summary_df = summary_df.sort_values("state").reset_index(drop=True)

        if not duration_df.empty and "state" in duration_df.columns:
            duration_df = duration_df.sort_values("state").reset_index(drop=True)

        return {
            "summary": summary_df,
            "duration_stats": duration_df,
        }
