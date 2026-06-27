import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ==========================================
# Imports
# ==========================================

from src.ingestion.market_data import MarketDataFetcher
from src.ingestion.vix_data import VIXDataFetcher
from src.ingestion.fii_dii_data import FIIDIIDataFetcher
from src.ingestion.data_merger import DataMerger

from src.features.feature_builder import FeatureBuilder

# ==========================================
# CONFIG
# ==========================================

START_DATE = "2022-01-01"

TICKERS = [
    "INFY.NS",
    "RELIANCE.NS"
]

# Equal weights
WEIGHTS = [
    0.5,
    0.5
]

# ==========================================
# MARKET RETURNS
# ==========================================

print("\n" + "=" * 70)
print("MARKET RETURNS")
print("=" * 70)

market_fetcher = MarketDataFetcher()

prices = market_fetcher.get_price_history(
    tickers=TICKERS,
    start_date=START_DATE
)

returns = market_fetcher.get_returns(
    prices
)

print("Price Shape:", prices.shape)
print("Returns Shape:", returns.shape)

# ==========================================
# INDIA VIX
# ==========================================

print("\n" + "=" * 70)
print("INDIA VIX")
print("=" * 70)

vix_fetcher = VIXDataFetcher()

vix = vix_fetcher.get_vix_history(
    START_DATE
)

vix = vix_fetcher.add_vix_change(
    vix,
    window=5
)

print("VIX Shape:", vix.shape)

# ==========================================
# FII DII
# ==========================================

print("\n" + "=" * 70)
print("FII / DII")
print("=" * 70)

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

print("FII/DII Shape:", fii_dii.shape)

# ==========================================
# DATA MERGER
# ==========================================

print("\n" + "=" * 70)
print("MERGING DATASETS")
print("=" * 70)

merger = DataMerger()

merged = merger.merge(
    returns_df=returns,
    vix_df=vix,
    fii_dii_df=fii_dii
)

merged = merger.clean(
    merged
)

print("Merged Shape:", merged.shape)

print("\nMerged Columns")

for col in merged.columns:
    print("-", col)

# ==========================================
# FEATURE BUILDER
# ==========================================

print("\n" + "=" * 70)
print("BUILDING FEATURES")
print("=" * 70)

builder = FeatureBuilder(
    volatility_window=20
)

feature_matrix = builder.build(
    merged_df=merged,
    weights=WEIGHTS
)

print("Feature Matrix Shape:", feature_matrix.shape)

print("\nFeature Columns")

for col in feature_matrix.columns:
    print("-", col)

# ==========================================
# DATA QUALITY
# ==========================================

print("\n" + "=" * 70)
print("DATA QUALITY")
print("=" * 70)

print("Missing Values:",
      feature_matrix.isna().sum().sum())

print("Duplicate Dates:",
      feature_matrix.index.duplicated().sum())

print("Infinite Values:",
      feature_matrix.isin(
          [float("inf"), float("-inf")]
      ).sum().sum())

# ==========================================
# DESCRIPTIVE STATISTICS
# ==========================================

print("\n" + "=" * 70)
print("FEATURE SUMMARY")
print("=" * 70)

print(
    feature_matrix.describe().T
)

# ==========================================
# SAMPLE DATA
# ==========================================

print("\n" + "=" * 70)
print("HEAD")
print("=" * 70)

print(
    feature_matrix.head()
)

print("\n" + "=" * 70)
print("TAIL")
print("=" * 70)

print(
    feature_matrix.tail()
)

# ==========================================
# CORRELATION MATRIX
# ==========================================

print("\n" + "=" * 70)
print("CORRELATION MATRIX")
print("=" * 70)

print(
    feature_matrix.corr().round(3)
)

# ==========================================
# READY FOR HMM?
# ==========================================

print("\n" + "=" * 70)
print("HMM READINESS")
print("=" * 70)

required_columns = [

    "portfolio_return",

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

# volatility column is dynamic
volatility_cols = [
    c for c in feature_matrix.columns
    if c.startswith("volatility_")
]

required_columns.extend(volatility_cols)

missing = [
    c
    for c in required_columns
    if c not in feature_matrix.columns
]

if len(missing) == 0:

    print("✓ All required features present")

else:

    print("Missing Features:")

    for m in missing:

        print("-", m)

print()

print(
    "Final Dataset Shape:",
    feature_matrix.shape
)

print(
    "Observations:",
    len(feature_matrix)
)

print(
    "Features:",
    len(feature_matrix.columns)
)

print("\nDataset Ready For Gaussian HMM ✓")