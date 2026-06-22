import pandas as pd

from src.features.returns import (
    ReturnFeature
)

from src.features.volatility import (
    VolatilityFeature
)

from src.features.drawdown import (
    DrawdownFeature
)


class FeatureBuilder:

    def __init__(
        self,
        volatility_window=20
    ):

        self.volatility_window = (
            volatility_window
        )

    def build(
        self,
        portfolio_returns: pd.Series
    ) -> pd.DataFrame:

        returns = (
            ReturnFeature.calculate(
                portfolio_returns
            )
        )

        volatility = (
            VolatilityFeature.calculate(
                portfolio_returns,
                window=self.volatility_window
            )
        )

        drawdown = (
            DrawdownFeature.calculate(
                portfolio_returns
            )
        )

        features = pd.concat(
            [
                returns,
                volatility,
                drawdown
            ],
            axis=1
        )

        features = (
            features.dropna()
        )

        return features