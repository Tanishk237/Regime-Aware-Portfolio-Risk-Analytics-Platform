import pandas as pd
import numpy as np
from pathlib import Path


np.random.seed(42)

# ====================================
# Business Days
# ====================================

dates = pd.bdate_range(
    start="2022-01-01",
    end="2025-12-31"
)

n = len(dates)

# ====================================
# Regime Generator
# ====================================

regimes = []

current_regime = "bull"

for _ in range(n):

    if np.random.rand() < 0.02:

        current_regime = np.random.choice(
            [
                "bull",
                "bear",
                "crisis",
                "high_vol"
            ]
        )

    regimes.append(current_regime)

# ====================================
# Generate Flows
# ====================================

fii = []
dii = []

for regime in regimes:

    if regime == "bull":

        fii_flow = np.random.normal(
            2500,
            1000
        )

        dii_flow = np.random.normal(
            -500,
            700
        )

    elif regime == "bear":

        fii_flow = np.random.normal(
            -2500,
            1200
        )

        dii_flow = np.random.normal(
            1800,
            800
        )

    elif regime == "crisis":

        fii_flow = np.random.normal(
            -6000,
            2000
        )

        dii_flow = np.random.normal(
            4000,
            1500
        )

    else:  # high_vol

        fii_flow = np.random.normal(
            0,
            3500
        )

        dii_flow = np.random.normal(
            0,
            2500
        )

    fii.append(round(fii_flow, 2))
    dii.append(round(dii_flow, 2))

# ====================================
# Build DataFrame
# ====================================

df = pd.DataFrame({
    "date": dates,
    "fii": fii,
    "dii": dii,
    "regime": regimes
})

df["net_flow"] = (
    df["fii"]
    +
    df["dii"]
)

# ====================================
# Save
# ====================================

output_dir = Path(
    "data/external"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True
)

output_file = (
    output_dir /
    "fii_dii.csv"
)

df.to_csv(
    output_file,
    index=False
)

print(
    f"Saved: {output_file}"
)

print(
    f"Rows: {len(df)}"
)

print(
    df.head()
)