from __future__ import annotations

from typing import Callable

from src.utils.scheduler import BackgroundScheduler


class MarketDataRefreshScheduler(BackgroundScheduler):
    def __init__(
        self,
        *,
        refresh_interval_seconds: int,
        refresh_job: Callable[[], None],
    ):
        super().__init__(
            name="market-data-refresh",
            interval_seconds=refresh_interval_seconds,
            job=refresh_job,
        )
