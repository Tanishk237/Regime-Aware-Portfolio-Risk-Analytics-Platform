import yfinance as yf
import pandas as pd


class MarketDataFetcher:

    @staticmethod
    def get_price_history(
        tickers,
        start_date,
        end_date=None
    ) -> pd.DataFrame:

        data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            auto_adjust=True,
            progress=False
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
