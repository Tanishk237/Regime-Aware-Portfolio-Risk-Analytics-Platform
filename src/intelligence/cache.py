from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class _CacheEntry:
    expires_at: float
    revision: str
    value: dict[str, Any]


class PortfolioAnalyticsCache:
    """Small process-local cache for expensive risk and regime payloads."""

    def __init__(self, max_entries: int = 1024) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._entries: dict[tuple[str, int], _CacheEntry] = {}
        self._lock = RLock()
        self.max_entries = max_entries

    def get(
        self,
        namespace: str,
        portfolio_id: int,
        revision: str,
    ) -> dict[str, Any] | None:
        key = (namespace, portfolio_id)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic() or entry.revision != revision:
                self._entries.pop(key, None)
                return None
            return deepcopy(entry.value)

    def set(
        self,
        namespace: str,
        portfolio_id: int,
        revision: str,
        value: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        if ttl_seconds <= 0:
            return
        with self._lock:
            now = monotonic()
            expired = [key for key, entry in self._entries.items() if entry.expires_at <= now]
            for expired_key in expired:
                self._entries.pop(expired_key, None)
            self._entries[(namespace, portfolio_id)] = _CacheEntry(
                expires_at=now + ttl_seconds,
                revision=revision,
                value=deepcopy(value),
            )
            while len(self._entries) > self.max_entries:
                oldest_key = min(
                    self._entries,
                    key=lambda key: self._entries[key].expires_at,
                )
                self._entries.pop(oldest_key, None)

    def invalidate(self, namespace: str, portfolio_id: int) -> None:
        with self._lock:
            self._entries.pop((namespace, portfolio_id), None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


portfolio_analytics_cache = PortfolioAnalyticsCache()


def database_cache_namespace(db: Session) -> str:
    return str(db.get_bind().url)


def invalidate_portfolio_intelligence(db: Session, portfolio_id: int) -> None:
    portfolio_analytics_cache.invalidate(database_cache_namespace(db), portfolio_id)
