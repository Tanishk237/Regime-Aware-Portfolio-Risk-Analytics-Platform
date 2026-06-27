import numpy as np
import pandas as pd


class FeatureValidator:
    """
    Performs validation checks on the final feature matrix.
    """

    @staticmethod
    def validate(df: pd.DataFrame):

        report = {}

        report["rows"] = len(df)

        report["columns"] = len(df.columns)

        report["missing_values"] = (
            df.isna()
            .sum()
            .sum()
        )

        report["duplicate_index"] = (
            df.index.duplicated()
            .sum()
        )

        report["infinite_values"] = (
            df.isin(
                [np.inf, -np.inf]
            )
            .sum()
            .sum()
        )

        report["feature_names"] = (
            list(df.columns)
        )

        return report

    @staticmethod
    def clean(df: pd.DataFrame):

        df = df.copy()

        df.replace(
            [np.inf, -np.inf],
            np.nan,
            inplace=True
        )

        df.dropna(
            inplace=True
        )

        return df

    @staticmethod
    def build_metadata(
        df: pd.DataFrame,
        config
    ):

        return {

            "n_samples": len(df),

            "n_features": len(df.columns),

            "feature_names": list(df.columns),

            "start_date": str(df.index.min()),

            "end_date": str(df.index.max()),

            "volatility_window":
                config.volatility_window,

            "flow_window":
                config.flow_window,

            "vix_window":
                config.vix_change_window

        }