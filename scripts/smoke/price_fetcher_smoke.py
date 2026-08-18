import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.portfolio.price_fetcher import PriceFetcher


fetcher = PriceFetcher()

tickers = [
    "RELIANCE.NS",
    "INFY.NS",
    "HDFCBANK.NS"
]

for ticker in tickers:

    price = fetcher.get_current_price(
        ticker,
        name=True
    )
    
    print(
        f"{ticker}: ₹{price[0]:.2f} ({price[1]})"
    )