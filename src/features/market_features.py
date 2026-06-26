import pandas as pd


class MarketFeatureBuilder:
    """
    These are exogenous market signals used by the HMM
    but are not portfolio-specific.
    """

    @staticmethod
    def build(
        merged_df: pd.DataFrame
    ) -> pd.DataFrame:

        features = pd.DataFrame(index=merged_df.index)

        # -------------------------
        # India VIX
        # -------------------------

        if "vix" in merged_df.columns:
            features["vix"] = merged_df["vix"]

        # -------------------------
        # VIX Change
        # -------------------------

        for column in merged_df.columns:

            if column.startswith("vix_change"):

                features[column] = merged_df[column]

        return features