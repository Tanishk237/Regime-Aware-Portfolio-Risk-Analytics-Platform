import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# =====================================
# Imports
# =====================================

from src.ingestion.market_data import MarketDataFetcher
from src.ingestion.vix_data import VIXDataFetcher
from src.ingestion.fii_dii_data import FIIDIIDataFetcher

# =====================================
# CONFIG
# =====================================

START_DATE = "2022-01-01"

TICKERS = [
    "RELIANCE.NS",
    "INFY.NS"
]

# =====================================
# MARKET DATA
# =====================================

print("\n" + "=" * 50)
print("MARKET DATA")
print("=" * 50)

market_fetcher = MarketDataFetcher()

prices = market_fetcher.get_price_history(
    TICKERS,
    START_DATE
)

print("\nColumns:")
print(prices.columns.tolist())

print("\nShape:")
print(prices.shape)

print("\nLatest Data:")
print(prices.tail())

# =====================================
# RETURNS
# =====================================

print("\n" + "=" * 50)
print("MARKET RETURNS")
print("=" * 50)

returns = market_fetcher.get_returns(
    prices
)

print("\nShape:")
print(returns.shape)

print("\nLatest Returns:")
print(returns.tail())

# =====================================
# NIFTY
# =====================================

print("\n" + "=" * 50)
print("NIFTY DATA")
print("=" * 50)

nifty = market_fetcher.get_nifty_history(
    START_DATE
)

print("\nShape:")
print(nifty.shape)

print("\nLatest Data:")
print(nifty.tail())

# =====================================
# INDIA VIX
# =====================================

print("\n" + "=" * 50)
print("INDIA VIX")
print("=" * 50)

vix_fetcher = VIXDataFetcher()

vix = vix_fetcher.get_vix_history(
    START_DATE
)

vix = vix_fetcher.add_vix_change(
    vix,
    window=5
)

print("\nColumns:")
print(vix.columns.tolist())

print("\nShape:")
print(vix.shape)

print("\nLatest Data:")
print(vix.tail())

# =====================================
# FII DII
# =====================================

print("\n" + "=" * 50)
print("FII DII DATA")
print("=" * 50)

csv_path = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "data"
    / "external"
    / "fii_dii.csv"
)

fii_dii = FIIDIIDataFetcher.load(
    csv_path
)

fii_dii = FIIDIIDataFetcher.add_net_flow(
    fii_dii
)

fii_dii = FIIDIIDataFetcher.add_rolling_features(
    fii_dii,
    window=20
)

print("\nColumns:")
print(fii_dii.columns.tolist())

print("\nShape:")
print(fii_dii.shape)

print("\nLatest Data:")
print(fii_dii.tail())

# =====================================
# DATA QUALITY
# =====================================

print("\n" + "=" * 50)
print("DATA QUALITY")
print("=" * 50)

print("\nMarket Data Missing:")
print(prices.isna().sum().sum())

print("\nReturns Missing:")
print(returns.isna().sum().sum())

print("\nVIX Missing:")
print(vix.isna().sum().sum())

print("\nFII/DII Missing:")
print(fii_dii.isna().sum().sum())

# =====================================
# REGIME DISTRIBUTION
# =====================================

if "regime" in fii_dii.columns:

    print("\n" + "=" * 50)
    print("REGIME DISTRIBUTION")
    print("=" * 50)

    print(
        fii_dii["regime"]
        .value_counts()
    )

# =====================================
# MERGE CHECK
# =====================================

print("\n" + "=" * 50)
print("MERGE CHECK")
print("=" * 50)

common_dates = (
    returns.index
    .intersection(vix.index)
    .intersection(fii_dii.index)
)

print(
    f"Common Dates Across All Sources: {len(common_dates)}"
)

print(
    f"Start Date: {common_dates.min()}"
)

print(
    f"End Date: {common_dates.max()}"
)

# =====================================
# FINAL STATUS
# =====================================

print("\n" + "=" * 50)
print("PIPELINE STATUS")
print("=" * 50)

print("✓ Market Data")
print("✓ Returns")
print("✓ NIFTY")
print("✓ India VIX")
print("✓ FII/DII")
print("✓ Date Alignment")

print("\nINGESTION LAYER OPERATIONAL")