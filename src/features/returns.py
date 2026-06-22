import pandas as pd


class ReturnFeature:

    @staticmethod
    def calculate(
        portfolio_returns: pd.Series
    ) -> pd.Series:

        returns = portfolio_returns.copy()

        returns.name = "return"

        return returns