import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.portfolio.trade_processor import create_trade
from src.portfolio.position_engine import PositionEngine
from src.portfolio.price_fetcher import PriceFetcher
from src.portfolio.pnl_engine import PnLEngine
from src.portfolio.weight_engine import WeightEngine

from src.ingestion.market_data import get_price_history
from src.portfolio.portfolio_returns import PortfolioReturnEngine


# =====================================
# STEP 1: Create Sample Trades
# =====================================

trades = [
    create_trade(
        "RELIANCE.NS",
        10,
        "2024-01-01",
        2500
    ),
    create_trade(
        "RELIANCE.NS",
        5,
        "2024-08-01",
        2900
    ),
    create_trade(
        "INFY.NS",
        20,
        "2024-03-15",
        1500
    )
]


# =====================================
# STEP 2: Build Positions
# =====================================

position_engine = PositionEngine()

positions = position_engine.build_positions(
    trades
)

print("\n==========================")
print("POSITIONS")
print("==========================")

print(positions)


# =====================================
# STEP 3: Fetch Current Prices
# =====================================

price_fetcher = PriceFetcher()

positions["current_price"] = positions[
    "ticker"
].apply(
    price_fetcher.get_current_price
)

print("\n==========================")
print("LIVE PRICES")
print("==========================")

print(positions)


# =====================================
# STEP 4: PnL Calculation
# =====================================

pnl_engine = PnLEngine()

positions = pnl_engine.calculate_pnl(
    positions
)

print("\n==========================")
print("P&L")
print("==========================")

print(
    positions[
        [
            "ticker",
            "cost_basis",
            "market_value",
            "profit",
            "profit_pct"
        ]
    ]
)


# =====================================
# STEP 5: Weight Calculation
# =====================================

weight_engine = WeightEngine()

positions = weight_engine.calculate_weights(
    positions
)

print("\n==========================")
print("WEIGHTS")
print("==========================")

print(
    positions[
        [
            "ticker",
            "weight"
        ]
    ]
)

print(
    "\nWeight Sum:",
    positions["weight"].sum()
)


# =====================================
# STEP 6: Historical Price Data
# =====================================

tickers = positions[
    "ticker"
].tolist()

price_history = get_price_history(
    tickers=tickers,
    start_date="2024-01-01"
)

print("\n==========================")
print("PRICE HISTORY")
print("==========================")

print(
    price_history.tail()
)


# =====================================
# STEP 7: Portfolio Returns
# =====================================

weights = dict(
    zip(
        positions["ticker"],
        positions["weight"]
    )
)

return_engine = PortfolioReturnEngine()

portfolio_returns = (
    return_engine.build_returns(
        price_history,
        weights
    )
)

print("\n==========================")
print("PORTFOLIO RETURNS")
print("==========================")

print(
    portfolio_returns.tail()
)


# =====================================
# STEP 8: Cumulative Returns
# =====================================

cumulative_returns = (
    return_engine.build_cumulative_returns(
        portfolio_returns
    )
)

print("\n==========================")
print("CUMULATIVE RETURNS")
print("==========================")

print(
    cumulative_returns.tail()
)


# =====================================
# STEP 9: Portfolio Summary
# =====================================

summary = return_engine.portfolio_summary(
    portfolio_returns
)

print("\n==========================")
print("SUMMARY")
print("==========================")

for k, v in summary.items():
    print(f"{k}: {v}")