import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.portfolio.position_engine import PositionEngine
from src.portfolio.trade_processor import create_trade


def test_position_engine_aggregates_trades_by_ticker():
    trades = [
        create_trade("RELIANCE.NS", 10, "2024-01-01", 2500),
        create_trade("RELIANCE.NS", 5, "2024-08-01", 2900),
        create_trade("INFY.NS", 20, "2024-03-15", 1500),
    ]

    positions = PositionEngine().build_positions(trades)
    positions = positions.set_index("ticker")

    assert positions.loc["RELIANCE.NS", "shares"] == 15
    assert round(positions.loc["RELIANCE.NS", "avg_cost"], 2) == 2633.33
    assert positions.loc["INFY.NS", "shares"] == 20
    assert positions.loc["INFY.NS", "avg_cost"] == 1500
