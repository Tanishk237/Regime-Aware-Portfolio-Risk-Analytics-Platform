import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ==========================================
# Portfolio Imports
# ==========================================

from src.portfolio.trade_processor import create_trade
from src.portfolio.position_engine import PositionEngine
from src.portfolio.price_fetcher import PriceFetcher
from src.portfolio.pnl_engine import PnLEngine
from src.portfolio.weight_engine import WeightEngine
from src.portfolio.portfolio_returns import PortfolioReturnEngine

# ==========================================
# Data Imports
# ==========================================

from src.ingestion.market_data import get_price_history

# ==========================================
# Risk Imports
# ==========================================

from src.risk.risk_engine import RiskEngine

# ==========================================
# STEP 1
# Create Sample Portfolio
# ==========================================

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

print("\n==========================")
print("TRADES")
print("==========================")
print(trades)

# ==========================================
# STEP 2
# Position Aggregation
# ==========================================

position_engine = PositionEngine()

positions = position_engine.build_positions(
    trades
)

print("\n==========================")
print("POSITIONS")
print("==========================")
print(positions)

# ==========================================
# STEP 3
# Current Prices
# ==========================================

fetcher = PriceFetcher()

positions["current_price"] = positions[
    "ticker"
].apply(
    fetcher.get_current_price
)

print("\n==========================")
print("LIVE PRICES")
print("==========================")
print(
    positions[
        [
            "ticker",
            "current_price"
        ]
    ]
)

# ==========================================
# STEP 4
# PnL
# ==========================================

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

# ==========================================
# STEP 5
# Weights
# ==========================================

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
            "cost_weight",
            "market_weight"
        ]
    ]
)

print(
    "\nWeight Sum:",
    positions["weight"].sum()
)

# ==========================================
# STEP 6
# Historical Prices
# ==========================================

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

# ==========================================
# STEP 7
# Portfolio Returns
# ==========================================

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

# ==========================================
# STEP 8
# Risk Engine
# ==========================================

risk_engine = RiskEngine()

risk_summary = risk_engine.analyze(
    portfolio_returns
)

print("\n==========================")
print("RISK SUMMARY")
print("==========================")

print(
    f"VaR (95%): {risk_summary.var_95:.4f}"
)

print(
    f"CVaR (95%): {risk_summary.cvar_95:.4f}"
)

print(
    f"Sharpe Ratio: {risk_summary.sharpe:.4f}"
)

print(
    f"Sortino Ratio: {risk_summary.sortino:.4f}"
)

print(
    f"Max Drawdown: {risk_summary.max_drawdown:.4f}"
)

print(
    f"Annualized Volatility: {risk_summary.volatility:.4f}"
)

# ==========================================
# PASS CHECK
# ==========================================

print("\n==========================")
print("PIPELINE STATUS")
print("==========================")

print(
    "Portfolio -> Returns -> Risk Engine SUCCESS"
)