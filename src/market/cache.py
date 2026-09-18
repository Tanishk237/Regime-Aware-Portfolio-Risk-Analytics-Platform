from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class MarketDataCache:
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        raise NotImplementedError


class InMemoryMarketDataCache(MarketDataCache):
    def __init__(self, max_entries: int = 512) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._items: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self.max_entries = max_entries

    def get(self, key: str) -> Optional[Any]:
        now = datetime.utcnow()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            now = datetime.utcnow()
            expired = [key for key, entry in self._items.items() if entry.expires_at <= now]
            for expired_key in expired:
                self._items.pop(expired_key, None)
            self._items[key] = CacheEntry(
                value=value,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


market_data_cache = InMemoryMarketDataCache()
