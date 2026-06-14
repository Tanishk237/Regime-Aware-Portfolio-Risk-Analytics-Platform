import pandas as pd


class PortfolioReturnEngine:

    def build_returns(
        self,
        returns_df,
        weights
    ):

        portfolio_returns = (
            returns_df * weights
        ).sum(axis=1)

        return portfolio_returns