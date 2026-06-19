import pandas as pd
import numpy as np


class PortfolioReturnEngine:

    def __init__(self):
        pass

    def calculate_asset_returns(
        self,
        price_history: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Convert price history into daily returns.
        """

        returns = price_history.pct_change()

        returns = returns.dropna()

        return returns

    def validate_weights(
        self,
        weights: dict
    ):

        total_weight = sum(weights.values())

        if not np.isclose(total_weight, 1.0):
            raise ValueError(
                f"Weights must sum to 1. Current sum = {total_weight}"
            )

    def build_returns(
        self,
        price_history: pd.DataFrame,
        weights: dict
    ) -> pd.Series:

        self.validate_weights(weights)

        asset_returns = self.calculate_asset_returns(
            price_history
        )

        weight_vector = pd.Series(weights)

        portfolio_returns = (
            asset_returns.mul(
                weight_vector,
                axis=1
            )
            .sum(axis=1)
        )

        portfolio_returns.name = "portfolio_return"

        return portfolio_returns

    def build_cumulative_returns(
        self,
        portfolio_returns: pd.Series
    ) -> pd.Series:

        cumulative_returns = (
            1 + portfolio_returns
        ).cumprod()

        return cumulative_returns

    def portfolio_summary(
        self,
        portfolio_returns: pd.Series
    ) -> dict:

        total_return = (
            (1 + portfolio_returns)
            .prod() - 1
        )

        annualized_return = (
            portfolio_returns.mean()
            * 252
        )

        annualized_volatility = (
            portfolio_returns.std()
            * np.sqrt(252)
        )

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility
        }