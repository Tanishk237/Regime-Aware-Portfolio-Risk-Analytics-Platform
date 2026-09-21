from __future__ import annotations

import logging
from threading import Event, Thread
from typing import Callable


logger = logging.getLogger(__name__)


class BackgroundScheduler:
    def __init__(
        self,
        *,
        name: str,
        interval_seconds: int,
        job: Callable[[], None],
    ):
        self.name = name
        self.interval_seconds = interval_seconds
        self.job = job
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run, name=self.name, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.job()
            except Exception:
                logger.exception("Scheduled job failed", extra={"job": self.name})
