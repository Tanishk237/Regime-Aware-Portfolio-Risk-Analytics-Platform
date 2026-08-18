import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ==========================================
# Imports
# ==========================================

from src.ingestion.market_data import (
    MarketDataFetcher
)

from src.ingestion.vix_data import (
    VIXDataFetcher
)

from src.ingestion.fii_dii_data import (
    FIIDIIDataFetcher
)

from src.ingestion.data_merger import (
    DataMerger
)

# ==========================================
# CONFIG
# ==========================================

START_DATE = "2022-01-01"

TICKERS = [
    "RELIANCE.NS",
    "INFY.NS"
]

# ==========================================
# MARKET RETURNS
# ==========================================

print("\n" + "=" * 60)
print("MARKET RETURNS")
print("=" * 60)

market_fetcher = MarketDataFetcher()

prices = market_fetcher.get_price_history(
    TICKERS,
    START_DATE
)

returns = market_fetcher.get_returns(
    prices
)

print("\nReturns Shape:")
print(returns.shape)

print("\nReturns Columns:")
print(returns.columns.tolist())

# ==========================================
# VIX
# ==========================================

print("\n" + "=" * 60)
print("VIX DATA")
print("=" * 60)

vix_fetcher = VIXDataFetcher()

vix = vix_fetcher.get_vix_history(
    START_DATE
)

vix = vix_fetcher.add_vix_change(
    vix,
    window=5
)

print("\nVIX Shape:")
print(vix.shape)

print("\nVIX Columns:")
print(vix.columns.tolist())

# ==========================================
# FII DII
# ==========================================

print("\n" + "=" * 60)
print("FII DII DATA")
print("=" * 60)

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

print("\nFII/DII Shape:")
print(fii_dii.shape)

print("\nFII/DII Columns:")
print(fii_dii.columns.tolist())

# ==========================================
# DATE ANALYSIS
# ==========================================

print("\n" + "=" * 60)
print("DATE COVERAGE")
print("=" * 60)

print(
    "\nReturns Range:",
    returns.index.min(),
    "->",
    returns.index.max()
)

print(
    "VIX Range:",
    vix.index.min(),
    "->",
    vix.index.max()
)

print(
    "FII/DII Range:",
    fii_dii.index.min(),
    "->",
    fii_dii.index.max()
)

# ==========================================
# MERGE
# ==========================================

print("\n" + "=" * 60)
print("MERGING")
print("=" * 60)

merger = DataMerger()

merged = merger.merge(
    returns,
    vix,
    fii_dii
)

print("\nMerged Shape Before Cleaning:")
print(merged.shape)

print("\nMerged Columns:")
print(merged.columns.tolist())

# ==========================================
# CLEAN
# ==========================================

merged_clean = merger.clean(
    merged
)

print("\nMerged Shape After Cleaning:")
print(merged_clean.shape)

# ==========================================
# QUALITY CHECKS
# ==========================================

print("\n" + "=" * 60)
print("QUALITY CHECKS")
print("=" * 60)

missing_values = (
    merged_clean
    .isna()
    .sum()
    .sum()
)

duplicate_dates = (
    merged_clean
    .index
    .duplicated()
    .sum()
)

infinite_values = (
    merged_clean
    .isin(
        [float("inf"), float("-inf")]
    )
    .sum()
    .sum()
)

print(
    "\nMissing Values:",
    missing_values
)

print(
    "Duplicate Dates:",
    duplicate_dates
)

print(
    "Infinite Values:",
    infinite_values
)

# ==========================================
# REGIME CHECK
# ==========================================

if "regime" in merged_clean.columns:

    print("\n" + "=" * 60)
    print("REGIME DISTRIBUTION")
    print("=" * 60)

    print(
        merged_clean["regime"]
        .value_counts()
    )

# ==========================================
# FEATURE READINESS
# ==========================================

print("\n" + "=" * 60)
print("FEATURE READINESS")
print("=" * 60)

required_columns = [
    "vix",
    "vix_change_5",
    "fii",
    "dii",
    "net_flow"
]

for column in required_columns:

    if column in merged_clean.columns:

        print(
            f"✓ {column}"
        )

    else:

        print(
            f"✗ {column}"
        )

# ==========================================
# SAMPLE DATA
# ==========================================

print("\n" + "=" * 60)
print("FINAL DATASET SAMPLE")
print("=" * 60)

print(
    merged_clean.tail(10)
)

# ==========================================
# FINAL STATUS
# ==========================================

print("\n" + "=" * 60)
print("FINAL STATUS")
print("=" * 60)

if (
    missing_values == 0
    and duplicate_dates == 0
    and infinite_values == 0
):

    print(
        "\n✓ INGESTION LAYER PASSED"
    )

    print(
        "✓ Ready For Feature Engineering"
    )

    print(
        "✓ Ready For HMM Training"
    )

else:

    print(
        "\n✗ Data Quality Issues Found"
    )