import numpy as np


class CVaRCalculator:

    @staticmethod
    def historical_cvar(
        returns,
        confidence_level=0.95
    ):

        percentile = (
            1 - confidence_level
        )

        var = np.quantile(
            returns,
            percentile
        )

        return returns[
            returns <= var
        ].mean()