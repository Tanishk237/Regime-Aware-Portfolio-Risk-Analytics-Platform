import pandas as pd


class DataMerger:

    @staticmethod
    def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
        idx = df.index

        if isinstance(idx, pd.MultiIndex):
            idx = idx.get_level_values(0)

        df = df.copy()
        df.index = pd.to_datetime(idx)

        return df

    @staticmethod
    def merge(
        returns_df,
        vix_df,
        fii_dii_df
    ):

        returns_df = DataMerger._ensure_datetime_index(returns_df)
        vix_df = DataMerger._ensure_datetime_index(vix_df)
        fii_dii_df = DataMerger._ensure_datetime_index(fii_dii_df)

        merged = (
            returns_df
            .join(vix_df, how="inner")
            .join(fii_dii_df, how="inner")
        )

        merged = merged.sort_index()

        return merged

    @staticmethod
    def clean(
        df
    ):

        df = (
            df
            .replace(
                [float("inf"), float("-inf")],
                pd.NA
            )
            .dropna()
        )

        return df