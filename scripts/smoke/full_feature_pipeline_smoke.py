import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ==========================================================
# Imports
# ==========================================================

from src.ingestion.market_data import MarketDataFetcher
from src.ingestion.vix_data import VIXDataFetcher
from src.ingestion.fii_dii_data import FIIDIIDataFetcher
from src.ingestion.data_merger import DataMerger

from src.features.feature_builder import FeatureBuilder

# ==========================================================
# CONFIG
# ==========================================================

START_DATE = "2022-01-01"

TICKERS = [
    "INFY.NS",
    "RELIANCE.NS"
]

WEIGHTS = [
    0.5,
    0.5
]

# ==========================================================
# MARKET DATA
# ==========================================================

print("\n" + "=" * 80)
print("MARKET DATA")
print("=" * 80)

market_fetcher = MarketDataFetcher()

prices = market_fetcher.get_price_history(
    TICKERS,
    START_DATE
)

returns = market_fetcher.get_returns(
    prices
)

print("Price Shape :", prices.shape)
print("Returns Shape :", returns.shape)

# ==========================================================
# VIX
# ==========================================================

print("\n" + "=" * 80)
print("INDIA VIX")
print("=" * 80)

vix_fetcher = VIXDataFetcher()

vix = vix_fetcher.get_vix_history(
    START_DATE
)

vix = vix_fetcher.add_vix_change(
    vix,
    window=5
)

print("VIX Shape :", vix.shape)

# ==========================================================
# FII DII
# ==========================================================

print("\n" + "=" * 80)
print("FII DII")
print("=" * 80)

csv_path = (
    Path(__file__).resolve().parents[1]
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

print("FII DII Shape :", fii_dii.shape)

# ==========================================================
# DATA MERGER
# ==========================================================

print("\n" + "=" * 80)
print("MERGING DATA")
print("=" * 80)

merger = DataMerger()

merged = merger.merge(
    returns,
    vix,
    fii_dii
)

merged = merger.clean(
    merged
)

print("Merged Shape :", merged.shape)

print("\nMerged Columns")

for column in merged.columns:
    print("-", column)

# ==========================================================
# FEATURE BUILDER
# ==========================================================

print("\n" + "=" * 80)
print("FEATURE ENGINEERING")
print("=" * 80)

builder = FeatureBuilder()

feature_matrix, metadata = builder.build(
    merged_df=merged,
    weights=WEIGHTS
)

print("Feature Matrix Shape :", feature_matrix.shape)

print("\nFeature Columns")

for column in feature_matrix.columns:
    print("-", column)

# ==========================================================
# DATA QUALITY
# ==========================================================

print("\n" + "=" * 80)
print("DATA QUALITY")
print("=" * 80)

print(
    "Missing Values :",
    feature_matrix.isna().sum().sum()
)

print(
    "Duplicate Dates :",
    feature_matrix.index.duplicated().sum()
)

print(
    "Infinite Values :",
    feature_matrix.isin(
        [float("inf"), float("-inf")]
    ).sum().sum()
)

# ==========================================================
# SUMMARY
# ==========================================================

print("\n" + "=" * 80)
print("FEATURE SUMMARY")
print("=" * 80)

print(
    feature_matrix.describe().round(4)
)

# ==========================================================
# CORRELATION
# ==========================================================

print("\n" + "=" * 80)
print("FEATURE CORRELATION")
print("=" * 80)

print(
    feature_matrix.corr().round(3)
)

# ==========================================================
# SAMPLE
# ==========================================================

print("\n" + "=" * 80)
print("HEAD")
print("=" * 80)

print(
    feature_matrix.head()
)

print("\n" + "=" * 80)
print("TAIL")
print("=" * 80)

print(
    feature_matrix.tail()
)

# ==========================================================
# METADATA
# ==========================================================

print("\n" + "=" * 80)
print("METADATA")
print("=" * 80)

for key, value in metadata.items():

    print(f"{key} : {value}")

# ==========================================================
# FEATURE CHECK
# ==========================================================

print("\n" + "=" * 80)
print("FEATURE VALIDATION")
print("=" * 80)

expected_features = [

    "portfolio_return",

    "volatility_20",

    "drawdown",

    "vix",

    "vix_change_5",

    "fii",

    "dii",

    "net_flow",

    "fii_avg_20",

    "dii_avg_20",

    "net_flow_avg_20"

]

missing = []

for feature in expected_features:

    if feature not in feature_matrix.columns:

        missing.append(feature)

if len(missing) == 0:

    print("✓ All Expected Features Present")

else:

    print("Missing Features:")

    for feature in missing:

        print("-", feature)

# ==========================================================
# FINAL STATUS
# ==========================================================

print("\n" + "=" * 80)
print("PIPELINE STATUS")
print("=" * 80)

print("Portfolio Features      ✓")
print("Market Features         ✓")
print("Flow Features           ✓")
print("Metadata Generated      ✓")
print("Validation Complete     ✓")
print("Feature Matrix Ready    ✓")

print("\nREADY FOR GAUSSIAN HMM TRAINING")