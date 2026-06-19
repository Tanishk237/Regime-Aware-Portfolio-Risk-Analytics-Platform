import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.portfolio.portfolio_returns import PortfolioReturnEngine


# ----------------------------------
# Sample Historical Prices
# ----------------------------------

price_history = pd.DataFrame(
    {
        "RELIANCE.NS": [100, 102, 101, 105, 107],
        "INFY.NS": [50, 51, 52, 51, 53]
    },
    index=pd.date_range(
        start="2024-01-01",
        periods=5
    )
)

# ----------------------------------
# Portfolio Weights
# ----------------------------------

weights = {
    "RELIANCE.NS": 0.60,
    "INFY.NS": 0.40
}

# ----------------------------------
# Engine
# ----------------------------------

engine = PortfolioReturnEngine()

# ----------------------------------
# Asset Returns
# ----------------------------------

asset_returns = engine.calculate_asset_returns(
    price_history
)

print("\nASSET RETURNS")
print(asset_returns)

# ----------------------------------
# Portfolio Returns
# ----------------------------------

portfolio_returns = engine.build_returns(
    price_history,
    weights
)

print("\nPORTFOLIO RETURNS")
print(portfolio_returns)

# ----------------------------------
# Cumulative Returns
# ----------------------------------

cumulative_returns = (
    engine.build_cumulative_returns(
        portfolio_returns
    )
)

print("\nCUMULATIVE RETURNS")
print(cumulative_returns)

# ----------------------------------
# Summary
# ----------------------------------

summary = engine.portfolio_summary(
    portfolio_returns
)

print("\nSUMMARY")
print(summary)