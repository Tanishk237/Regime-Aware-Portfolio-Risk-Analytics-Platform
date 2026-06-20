import numpy as np


class SharpeCalculator:

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

        return (
            np.sqrt(252)
            *
            excess_returns.mean()
            /
            excess_returns.std()
        )