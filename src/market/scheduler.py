from __future__ import annotations

import logging
from datetime import date
from threading import Event, Thread
from typing import Callable


logger = logging.getLogger(__name__)


class MarketDataRefreshScheduler:
    def __init__(
        self,
        *,
        refresh_interval_seconds: int,
        refresh_job: Callable[[], None],
    ):
        self.refresh_interval_seconds = refresh_interval_seconds
        self.refresh_job = refresh_job
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run, name="market-data-refresh", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self.refresh_interval_seconds):
            try:
                self.refresh_job()
            except Exception:
                logger.exception("Scheduled market data refresh failed.")
