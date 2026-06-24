import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.data_merger import DataMerger

# Create returns_df with single DatetimeIndex
dates = pd.date_range(start="2022-01-01", periods=10, freq='D')
returns_df = pd.DataFrame({"RET": range(10)}, index=dates)

# Create vix_df with a MultiIndex index (date, source)
dates_multi = [(d, 'x') for d in dates]
mi_index = pd.MultiIndex.from_tuples(dates_multi, names=["date", "src"])
vix_df = pd.DataFrame({"vix": range(10)}, index=mi_index)

# Create fii_dii_df with single DatetimeIndex
fii_dii_df = pd.DataFrame({"fii": range(10,20)}, index=dates)

print("returns_df.index.nlevels:", returns_df.index.nlevels)
print("vix_df.index.nlevels:", vix_df.index.nlevels)
print("fii_dii_df.index.nlevels:", fii_dii_df.index.nlevels)

merged = DataMerger.merge(returns_df, vix_df, fii_dii_df)

print("Merged shape:", merged.shape)
print(merged.head())
