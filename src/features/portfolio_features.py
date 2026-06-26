import pandas as pd

from src.features.returns import ReturnFeature
from src.features.volatility import VolatilityFeature
from src.features.drawdown import DrawdownFeature


class PortfolioFeatureBuilder:
    """
    Builds portfolio-specific features.

    These features are derived purely from the
    portfolio return series and are independent
    of external market data.
    """

    def __init__(
        self,
        volatility_window: int = 20,
        annualize_volatility: bool = True
    ):

        self.volatility_window = volatility_window
        self.annualize_volatility = annualize_volatility

    def build(
        self,
        portfolio_returns: pd.Series
    ) -> pd.DataFrame:
        """
        Parameters
        ----------
        portfolio_returns : pd.Series
            Daily portfolio returns.

        Returns
        -------
        pd.DataFrame
            Portfolio feature matrix.
        """

        features = pd.DataFrame(
            index=portfolio_returns.index
        )

        # -----------------------------
        # Daily Return
        # -----------------------------

        returns = ReturnFeature.calculate(
            portfolio_returns
        )

        features[returns.name] = returns

        # -----------------------------
        # Rolling Volatility
        # -----------------------------

        volatility = VolatilityFeature.calculate(
            portfolio_returns=portfolio_returns,
            window=self.volatility_window,
            annualize=self.annualize_volatility
        )

        features[volatility.name] = volatility

        # -----------------------------
        # Drawdown
        # -----------------------------

        drawdown = DrawdownFeature.calculate(
            portfolio_returns
        )

        features[drawdown.name] = drawdown

        return features