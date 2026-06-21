import numpy as np

from src.risk.var import VaRCalculator
from src.risk.cvar import CVaRCalculator
from src.risk.sharpe import SharpeCalculator
from src.risk.sortino import SortinoCalculator
from src.risk.drawdown_metrics import DrawdownCalculator
from src.risk.risk_summary import RiskSummary


class RiskEngine:

    def __init__(
        self,
        confidence_level=0.95,
        risk_free_rate=0.06
    ):
        self.confidence_level = confidence_level
        self.risk_free_rate = risk_free_rate

    def analyze(
        self,
        portfolio_returns
    ) -> RiskSummary:

        # ----------------------------
        # VaR
        # ----------------------------

        var_95 = (
            VaRCalculator
            .historical_var(
                portfolio_returns,
                self.confidence_level
            )
        )

        # ----------------------------
        # CVaR
        # ----------------------------

        cvar_95 = (
            CVaRCalculator
            .historical_cvar(
                portfolio_returns,
                self.confidence_level
            )
        )

        # ----------------------------
        # Sharpe
        # ----------------------------

        sharpe = (
            SharpeCalculator
            .calculate(
                portfolio_returns,
                self.risk_free_rate
            )
        )

        # ----------------------------
        # Sortino
        # ----------------------------

        sortino = (
            SortinoCalculator
            .calculate(
                portfolio_returns,
                self.risk_free_rate
            )
        )

        # ----------------------------
        # Drawdown
        # ----------------------------

        drawdown_data = (
            DrawdownCalculator
            .calculate(
                portfolio_returns
            )
        )

        max_drawdown = (
            drawdown_data[
                "max_drawdown"
            ]
        )

        # ----------------------------
        # Annualized Volatility
        # ----------------------------

        annualized_volatility = (
            portfolio_returns.std()
            * np.sqrt(252)
        )

        # ----------------------------
        # Return Summary Object
        # ----------------------------

        return RiskSummary(
            var_95=var_95,
            cvar_95=cvar_95,
            sharpe=sharpe,
            sortino=sortino,
            max_drawdown=max_drawdown,
            volatility=annualized_volatility
        )