import pandas as pd


class DrawdownFeature:

    @staticmethod
    def calculate(
        portfolio_returns: pd.Series
    ) -> pd.Series:

        cumulative = (
            1 + portfolio_returns
        ).cumprod()

        rolling_peak = (
            cumulative.cummax()
        )

        drawdown = (
            cumulative
            /
            rolling_peak
        ) - 1

        drawdown.name = "drawdown"

        return drawdown