import pandas as pd


class FlowFeatureBuilder:
    """
    These features capture foreign and domestic
    institutional participation in the market.
    """

    FLOW_COLUMNS = [

        "fii",
        "dii",
        "net_flow",

        "fii_avg_20",
        "dii_avg_20",
        "net_flow_avg_20"

    ]

    @classmethod
    def build(
        cls,
        merged_df: pd.DataFrame
    ) -> pd.DataFrame:

        features = pd.DataFrame(index=merged_df.index)

        for column in cls.FLOW_COLUMNS:

            if column in merged_df.columns:

                features[column] = merged_df[column]

        return features