from dataclasses import dataclass


@dataclass
class RiskSummary:

    var_95: float

    cvar_95: float

    sharpe: float

    sortino: float

    max_drawdown: float

    volatility: float