import pandas as pd
import numpy as np


class VolatilityFeature:

    @staticmethod
    def calculate(
        portfolio_returns: pd.Series,
        window: int = 20,
        annualize: bool = True
    ) -> pd.Series:

        volatility = (
            portfolio_returns
            .rolling(window)
            .std()
        )

        if annualize:

            volatility = (
                volatility
                * np.sqrt(252)
            )

        volatility.name = (
            f"volatility_{window}"
        )

        return volatility