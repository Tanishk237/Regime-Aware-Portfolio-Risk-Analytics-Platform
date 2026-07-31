import pandas as pd

from src.market.providers import YahooFinanceProvider


class MarketDataFetcher:

    @staticmethod
    def get_price_history(
        tickers,
        start_date,
        end_date=None
    ) -> pd.DataFrame:

        normalized_tickers = (
            tickers
            if isinstance(tickers, list)
            else [tickers]
        )
        data = YahooFinanceProvider().get_ohlcv(
            normalized_tickers,
            start_date,
            end_date,
        )

        if "Close" in data:
            data = data["Close"]

        return data.dropna(how="all")

    @staticmethod
    def get_returns(
        price_history: pd.DataFrame
    ) -> pd.DataFrame:

        returns = (
            price_history
            .pct_change()
            .dropna()
        )

        return returns

    @staticmethod
    def get_nifty_history(
        start_date,
        end_date=None
    ):

        return MarketDataFetcher.get_price_history(
            "^NSEI",
            start_date,
            end_date
        )


def get_price_history(
    tickers,
    start_date,
    end_date=None
) -> pd.DataFrame:
    """
    Backward-compatible module-level wrapper used by older pipeline scripts.
    """

    return MarketDataFetcher.get_price_history(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date
    )
