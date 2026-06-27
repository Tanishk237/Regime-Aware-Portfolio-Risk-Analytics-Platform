import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import numpy as np

from src.features.portfolio_features import PortfolioFeatureBuilder

np.random.seed(42)

returns = pd.Series(
    np.random.normal(
        0.001,
        0.02,
        250
    ),
    index=pd.date_range(
        "2024-01-01",
        periods=250
    )
)

builder = PortfolioFeatureBuilder(
    volatility_window=20
)

features = builder.build(
    returns
)

print(features.head())

print()

print(features.columns)

print()

print(features.describe())