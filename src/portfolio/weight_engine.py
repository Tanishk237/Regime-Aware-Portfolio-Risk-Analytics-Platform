import pandas as pd


class WeightEngine:

    def calculate_weights(
        self,
        positions: pd.DataFrame
    ):

        total_value = positions[
            "market_value"
        ].sum()

        positions["weight"] = (
            positions["market_value"]
            /
            total_value
        )

        return positions