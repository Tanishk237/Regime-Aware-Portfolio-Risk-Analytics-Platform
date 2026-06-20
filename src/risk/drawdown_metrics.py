import pandas as pd


class DrawdownCalculator:

    @staticmethod
    def calculate(
        portfolio_returns
    ):

        cumulative = (
            1 + portfolio_returns
        ).cumprod()
        
        rolling_max = (
            cumulative.cummax()
        )

        drawdown = (
            cumulative
            /
            rolling_max
        ) - 1

        max_drawdown = (
            drawdown.min()
        )

        return {
            "drawdown_series":
                drawdown,
            "max_drawdown":
                max_drawdown
        }