import pandas as pd


class WeightEngine:

    def calculate_weights(
        self,
        positions: pd.DataFrame
    ) -> pd.DataFrame:

        total_market_value = positions[
            "market_value"
        ].sum()

        total_cost_basis = positions[
            "cost_basis"
        ].sum()

        positions["market_weight"] = (
            positions["market_value"]
            /
            total_market_value
        )

        positions["cost_weight"] = (
            positions["cost_basis"]
            /
            total_cost_basis
        )

        # Backward compatibility
        positions["weight"] = positions[
            "market_weight"
        ]

        return positions