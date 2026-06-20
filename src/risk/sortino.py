import numpy as np

# Only calculates the downside part of the Sharpe ratio, which is the standard deviation of negative returns. This is used to calculate the Sortino ratio, which is a variation of the Sharpe ratio that only considers downside volatility.
class SortinoCalculator:

    @staticmethod
    def calculate(
        returns,
        risk_free_rate=0.06
    ):

        daily_rf = (
            risk_free_rate / 252
        )

        excess_returns = (
            returns - daily_rf
        )

        downside = excess_returns[
            excess_returns < 0
        ]

        downside_std = (
            downside.std()
        )

        return (
            np.sqrt(252)
            *
            excess_returns.mean()
            /
            downside_std
        )