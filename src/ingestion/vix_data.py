import yfinance as yf
import pandas as pd


class VIXDataFetcher:

    @staticmethod
    def get_vix_history(
        start_date,
        end_date=None
    ) -> pd.DataFrame:

        vix = yf.download(
            "^INDIAVIX",
            start=start_date,
            end=end_date,
            auto_adjust=True,
            progress=False
        )

        vix = vix[["Close"]].rename(columns={"Close": "vix"})

        return vix

    @staticmethod
    def add_vix_change(
        vix_df,
        window=5
    ):

        vix_df[
            f"vix_change_{window}"
        ] = (
            vix_df["vix"]
            .pct_change(window)
        )

        return vix_df