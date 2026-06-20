import numpy as np


class VaRCalculator:

    @staticmethod
    def historical_var(
        returns,
        confidence_level=0.95
    ):

        percentile = (
            1 - confidence_level
        ) * 100

        return np.percentile(
            returns,
            percentile
        )