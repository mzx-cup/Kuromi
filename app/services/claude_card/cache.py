"""In-memory cache for project state — key by commit_sha, TTL 1h."""
from __future__ import annotations

import time
from typing import Optional


class ClaudeCardCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Optional[str]:
        if key not in self._store:
            return None
        written_at, value = self._store[key]
        if time.time() - written_at > 3600:
            return None
        return value

    def set(self, key: str, value: str) -> None:
        self._store[key] = (time.time(), value)
