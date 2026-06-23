import pandas as pd


class FIIDIIDataFetcher:

    @staticmethod
    def load(
        filepath
    ):

        df = pd.read_csv(
            filepath
        )

        df["date"] = pd.to_datetime(
            df["date"]
        )

        df = df.set_index(
            "date"
        )

        return df

    @staticmethod
    def add_net_flow(
        df
    ):

        df["net_flow"] = (
            df["fii"]
            +
            df["dii"]
        )

        return df

    @staticmethod
    def add_rolling_features(
        df,
        window=20
    ):

        df[
            f"fii_avg_{window}"
        ] = (
            df["fii"]
            .rolling(window)
            .mean()
        )

        df[
            f"dii_avg_{window}"
        ] = (
            df["dii"]
            .rolling(window)
            .mean()
        )

        df[
            f"net_flow_avg_{window}"
        ] = (
            df["net_flow"]
            .rolling(window)
            .mean()
        )

        return df