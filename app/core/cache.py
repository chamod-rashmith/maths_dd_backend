"""
Hybrid Caching Engine:
Primary: Upstash Serverless Redis (via high-speed REST API).
Fallback: In-Memory Thread-Safe TTLCache (offline/dev fallback).
"""

import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("maths_dd.cache")


class InMemoryTTLCache:
    """Lightweight in-memory cache with time-to-live (TTL) expiration and prefix invalidation."""

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = (time.monotonic() + ttl, value)

    def invalidate_prefix(self, prefix: str) -> None:
        keys_to_remove = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_remove:
            self._store.pop(k, None)

    def clear(self) -> None:
        self._store.clear()


class HybridCache:
    """
    Unified caching interface.
    Attempts Upstash Serverless Redis; gracefully falls back to InMemoryTTLCache on any error.
    """

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        self._default_ttl = default_ttl_seconds
        self._memory_fallback = InMemoryTTLCache(default_ttl_seconds=default_ttl_seconds)
        self._upstash_client = None
        self._init_upstash()

    def _init_upstash(self) -> None:
        if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
            try:
                from upstash_redis import Redis

                self._upstash_client = Redis(
                    url=settings.UPSTASH_REDIS_REST_URL,
                    token=settings.UPSTASH_REDIS_REST_TOKEN,
                )
                logger.info("Upstash Serverless Redis client initialized successfully.")
            except Exception as exc:
                logger.warning("Failed to initialize Upstash Redis (using in-memory): %s", exc)
                self._upstash_client = None

    def get(self, key: str) -> Optional[Any]:
        """Retrieves cached item from Upstash Redis or In-Memory fallback."""
        if self._upstash_client:
            try:
                raw = self._upstash_client.get(key)
                if raw is not None:
                    # Upstash automatically decodes or returns string/dict
                    if isinstance(raw, str):
                        try:
                            return json.loads(raw)
                        except json.JSONDecodeError:
                            return raw
                    return raw
            except Exception as exc:
                logger.warning("Upstash GET error for key '%s' (falling back to memory): %s", key, exc)

        return self._memory_fallback.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Stores item with TTL in Upstash Redis and In-Memory fallback."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl

        # Always update memory fallback for ultra-low latency & resilience
        self._memory_fallback.set(key, value, ttl_seconds=ttl)

        if self._upstash_client:
            try:
                serialized = json.dumps(value, default=str) if not isinstance(value, (str, int, float, bool)) else value
                self._upstash_client.set(key, serialized, ex=ttl)
            except Exception as exc:
                logger.warning("Upstash SET error for key '%s': %s", key, exc)

    def invalidate_prefix(self, prefix: str) -> None:
        """Invalidates keys starting with prefix across both Upstash Redis and In-Memory."""
        self._memory_fallback.invalidate_prefix(prefix)

        if self._upstash_client:
            try:
                # Find all keys matching prefix*
                matching_keys = self._upstash_client.keys(f"{prefix}*")
                if matching_keys:
                    self._upstash_client.delete(*matching_keys)
            except Exception as exc:
                logger.warning("Upstash invalidate_prefix error for '%s': %s", prefix, exc)

    def clear(self) -> None:
        self._memory_fallback.clear()
        if self._upstash_client:
            try:
                self._upstash_client.flushdb()
            except Exception as exc:
                logger.warning("Upstash flushdb error: %s", exc)


# Global curriculum & reference data cache
curriculum_cache = HybridCache(default_ttl_seconds=3600)

# Global study notes catalog & detail cache
study_notes_cache = HybridCache(default_ttl_seconds=3600)
