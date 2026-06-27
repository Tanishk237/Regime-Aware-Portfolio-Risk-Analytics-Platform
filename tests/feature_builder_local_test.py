import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.feature_builder import FeatureBuilder

# Create sample data
dates = pd.date_range('2022-01-01', periods=100, freq='D')
returns = pd.DataFrame({
    'INFY.NS': [0.01 if i % 2 == 0 else -0.01 for i in range(100)],
    'RELIANCE.NS': [0.02 if i % 3 == 0 else -0.015 for i in range(100)],
    'vix': [15 + i*0.1 for i in range(100)],
    'fii': [1000 - i*10 for i in range(100)]
}, index=dates)

weights = [0.5, 0.5]

# Test build with merged_df and weights
builder = FeatureBuilder(volatility_window=20)

try:
    feature_matrix = builder.build(
        merged_df=returns,
        weights=weights
    )
    print("✓ Feature builder accepted merged_df and weights")
    print(f"Feature matrix shape: {feature_matrix.shape}")
    print(f"Columns: {list(feature_matrix.columns)}")
except Exception as e:
    print(f"✗ Error: {e}")
