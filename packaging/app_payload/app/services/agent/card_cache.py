"""Field-level TTL cache for memory cards."""
from __future__ import annotations

import time
from typing import Optional


class CardCache:
    """In-memory key→str cache. TTL defaults to 300s (5 min)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str, float]] = {}
        # key -> (written_at_ts, value, ttl_s)

    def set(self, key: str, value: str, ttl_s: int = 300) -> None:
        self._store[key] = (time.time(), value, ttl_s)

    def get(self, key: str, *, now_ts: Optional[float] = None) -> Optional[str]:
        if key not in self._store:
            return None
        written_at, value, ttl_s = self._store[key]
        now = now_ts if now_ts is not None else time.time()
        if now - written_at > ttl_s:
            return None
        return value
