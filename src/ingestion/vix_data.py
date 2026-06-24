import yfinance as yf
import pandas as pd


class VIXDataFetcher:

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = [
                col[-1] if isinstance(col, tuple) and len(col) > 1 else col
                for col in df.columns
            ]
        return df

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

        if isinstance(vix.columns, pd.MultiIndex) and "Close" in vix.columns.get_level_values(0):
            vix = vix["Close"]

        if isinstance(vix, pd.Series):
            vix = vix.to_frame(name="vix")
        else:
            vix = VIXDataFetcher._flatten_columns(vix)
            if vix.shape[1] == 1:
                vix.columns = ["vix"]

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