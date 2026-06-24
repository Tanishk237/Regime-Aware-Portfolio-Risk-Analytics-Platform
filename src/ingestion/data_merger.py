import pandas as pd


class DataMerger:

    @staticmethod
    def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
        idx = df.index

        if isinstance(idx, pd.MultiIndex):
            for lev in range(idx.nlevels):
                lv = idx.get_level_values(lev)
                try:
                    dt = pd.to_datetime(lv)
                    df = df.copy()
                    df.index = dt
                    return df
                except Exception:
                    continue

            # Fallback: use first level
            idx = idx.get_level_values(0)

        df = df.copy()
        df.index = pd.to_datetime(idx)

        return df

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = [
                "_".join(
                    str(c) for c in col if c not in (None, "")
                ).rstrip("_")
                for col in df.columns
            ]
        return df

    @staticmethod
    def merge(
        returns_df,
        vix_df,
        fii_dii_df
    ):

        returns_df = DataMerger._flatten_columns(
            DataMerger._ensure_datetime_index(returns_df)
        )
        vix_df = DataMerger._flatten_columns(
            DataMerger._ensure_datetime_index(vix_df)
        )
        fii_dii_df = DataMerger._flatten_columns(
            DataMerger._ensure_datetime_index(fii_dii_df)
        )

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