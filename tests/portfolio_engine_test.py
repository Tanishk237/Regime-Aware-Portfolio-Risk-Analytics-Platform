import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.portfolio.trade_processor import create_trade
from src.portfolio.position_engine import PositionEngine

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

engine = PositionEngine()

positions = engine.build_positions(trades)

print(positions)