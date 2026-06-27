from dataclasses import dataclass


@dataclass
class FeatureConfig:
    """
    Central configuration for feature engineering.

    All tunable parameters used across the feature engineering
    pipeline should live here so they can later be exposed
    directly in the Streamlit dashboard.
    """

    # -----------------------------------------
    # Portfolio Features
    # -----------------------------------------

    annualize_volatility: bool = True

    trading_days: int = 252

    # -----------------------------------------
    # Rolling Windows
    # -----------------------------------------

    volatility_window: int = 20

    drawdown_window: int = 252

    flow_window: int = 20

    vix_change_window: int = 5

    # -----------------------------------------
    # Data Cleaning
    # -----------------------------------------

    drop_missing: bool = True

    replace_infinite: bool = True

    # -----------------------------------------
    # Validation
    # -----------------------------------------

    minimum_rows: int = 200

    minimum_features: int = 5