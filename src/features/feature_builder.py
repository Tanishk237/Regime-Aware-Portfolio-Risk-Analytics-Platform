import pandas as pd

from src.features.feature_config import FeatureConfig
from src.features.feature_validator import FeatureValidator

from src.features.portfolio_features import (
    PortfolioFeatureBuilder
)

from src.features.market_features import (
    MarketFeatureBuilder
)

from src.features.flow_features import (
    FlowFeatureBuilder
)


class FeatureBuilder:
    """
    Master Feature Builder.

    This class orchestrates all feature engineering modules
    and produces the final feature matrix used for HMM training.
    """

    def __init__(
        self,
        config: FeatureConfig = None,
        **config_overrides
    ):

        self.config = config or FeatureConfig()

        for key, value in config_overrides.items():
            if not hasattr(self.config, key):
                raise TypeError(
                    f"Unknown FeatureConfig option: {key}"
                )

            setattr(
                self.config,
                key,
                value
            )

        self.portfolio_builder = PortfolioFeatureBuilder(
            volatility_window=self.config.volatility_window,
            annualize_volatility=self.config.annualize_volatility
        )

        self.validator = FeatureValidator()

    # ---------------------------------------------------
    # Portfolio Returns
    # ---------------------------------------------------

    @staticmethod
    def build_portfolio_returns(
        returns_df: pd.DataFrame,
        weights=None
    ) -> pd.Series:
        """
        Builds weighted portfolio returns.
        """

        if weights is None:

            weights = [
                1 / len(returns_df.columns)
            ] * len(returns_df.columns)

        portfolio_returns = (
            returns_df
            .mul(weights, axis=1)
            .sum(axis=1)
        )

        portfolio_returns.name = "portfolio_return"

        return portfolio_returns

    # ---------------------------------------------------
    # Main Build Pipeline
    # ---------------------------------------------------

    def build(
        self,
        merged_df: pd.DataFrame,
        weights=None
    ):
        """
        Parameters
        ----------
        merged_df

            Output from DataMerger.

        weights

            Portfolio weights.

        Returns
        -------

        feature_matrix

        metadata
        """

        # ---------------------------------------------
        # Asset Return Columns
        # ---------------------------------------------

        asset_columns = [

            column

            for column in merged_df.columns

            if column.endswith(".NS")

        ]

        returns_df = merged_df[
            asset_columns
        ]

        # ---------------------------------------------
        # Portfolio Returns
        # ---------------------------------------------

        portfolio_returns = self.build_portfolio_returns(
            returns_df,
            weights
        )

        # ---------------------------------------------
        # Portfolio Features
        # ---------------------------------------------

        portfolio_features = (
            self.portfolio_builder.build(
                portfolio_returns
            )
        )

        # Rename "return" to "portfolio_return"

        portfolio_features = (
            portfolio_features.rename(
                columns={
                    "return": "portfolio_return"
                }
            )
        )

        # ---------------------------------------------
        # Market Features
        # ---------------------------------------------

        market_features = (
            MarketFeatureBuilder.build(
                merged_df
            )
        )

        # ---------------------------------------------
        # Flow Features
        # ---------------------------------------------

        flow_features = (
            FlowFeatureBuilder.build(
                merged_df
            )
        )

        # ---------------------------------------------
        # Combine Everything
        # ---------------------------------------------

        feature_matrix = pd.concat(

            [

                portfolio_features,

                market_features,

                flow_features

            ],

            axis=1

        )

        # ---------------------------------------------
        # Clean
        # ---------------------------------------------

        feature_matrix = self.validator.clean(
            feature_matrix
        )

        # ---------------------------------------------
        # Validation Report
        # ---------------------------------------------

        validation_report = self.validator.validate(
            feature_matrix
        )

        # ---------------------------------------------
        # Metadata
        # ---------------------------------------------

        metadata = self.validator.build_metadata(

            feature_matrix,

            self.config

        )

        metadata[
            "validation"
        ] = validation_report

        return (

            feature_matrix,

            metadata

        )
