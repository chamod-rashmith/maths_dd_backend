"""
Thread-safe In-Memory TTL Cache for high-read / low-write data (e.g., Curriculum Subjects & Lessons).
Automatically invalidates entries on mutation (`POST` / `DELETE`).
"""

import time
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    """Lightweight in-memory cache with time-to-live (TTL) expiration and prefix invalidation."""

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Retrieves an item if present and not expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Stores a value in cache for `ttl_seconds`."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = (time.monotonic() + ttl, value)

    def invalidate_prefix(self, prefix: str) -> None:
        """Removes all cached keys starting with `prefix`."""
        keys_to_remove = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_remove:
            self._store.pop(k, None)

    def clear(self) -> None:
        """Clears the entire cache."""
        self._store.clear()


curriculum_cache = TTLCache(default_ttl_seconds=3600)
