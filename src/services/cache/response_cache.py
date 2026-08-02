"""Response cache for AI Curator chat answers.

Adapted from AI Portfolio ResponseCache with JSON persistence, TTL,
invalidation and hit statistics.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from config import settings


class CacheStats(BaseModel):
    """Cache hit/miss statistics."""

    total_hits: int = 0
    total_misses: int = 0
    total_sets: int = 0
    total_invalidations: int = 0
    total_expired: int = 0
    cache_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Hit rate percentage."""
        total = self.total_hits + self.total_misses
        if total == 0:
            return 0.0
        return (self.total_hits / total) * 100


class CacheEntry(BaseModel):
    """A single cache entry."""

    query_hash: str
    query: str
    response: str
    created_at: float
    expires_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Return True when the entry TTL has passed."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class ResponseCache:
    """JSON-persistent response cache with TTL and statistics."""

    def __init__(
        self,
        cache_file: str = settings.cache_file_path,
        ttl_seconds: int = settings.cache_ttl_seconds,
        enable_persistence: bool = True,
    ):
        self.cache_file = Path(cache_file)
        self.ttl_seconds = ttl_seconds
        self.enable_persistence = enable_persistence
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._load_cache()

    @staticmethod
    def build_cache_key(
        message: str,
        role: Optional[str] = None,
        difficulty: Optional[str] = None,
        course_id: Optional[int] = None,
        intent: Optional[str] = None,
    ) -> str:
        """Return a stable SHA-256 key from request parameters.

        The key intentionally covers the user-visible parameters that shape the
        answer: message text, demo role, difficulty level, selected course and
        classified intent. History is excluded because the assistant is expected
        to answer the latest message on its own.
        """
        normalized = " ".join((message or "").lower().split())
        payload = "|".join(
            [
                normalized,
                role or "",
                difficulty or "",
                str(course_id) if course_id is not None else "",
                intent or "",
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, query: str) -> Optional[str]:
        """Return a cached response string or None."""
        cache_key = self.build_cache_key(query)
        return self.get_by_key(cache_key)

    def get_by_key(self, cache_key: str) -> Optional[str]:
        """Return a cached response string by pre-computed key."""
        entry = self._cache.get(cache_key)
        if entry is None:
            self._stats.total_misses += 1
            return None
        if entry.is_expired():
            self._stats.total_expired += 1
            self._stats.total_misses += 1
            del self._cache[cache_key]
            self._save_cache()
            return None
        self._stats.total_hits += 1
        return entry.response

    def get_entry(self, query: str) -> Optional[CacheEntry]:
        """Return the full cache entry for a query."""
        cache_key = self.build_cache_key(query)
        return self.get_entry_by_key(cache_key)

    def get_entry_by_key(self, cache_key: str) -> Optional[CacheEntry]:
        """Return the full cache entry by pre-computed key."""
        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        if entry.is_expired():
            self._stats.total_expired += 1
            del self._cache[cache_key]
            self._save_cache()
            return None
        return entry

    def set(
        self,
        query: str,
        response: str,
        metadata: Optional[dict] = None,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """Store a response in the cache."""
        cache_key = self.build_cache_key(query)
        return self.set_by_key(cache_key, query, response, metadata, ttl_seconds)

    def set_by_key(
        self,
        cache_key: str,
        query: str,
        response: str,
        metadata: Optional[dict] = None,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """Store a response under a pre-computed key."""
        now = time.time()
        effective_ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        expires_at = None
        if effective_ttl and effective_ttl > 0:
            expires_at = now + effective_ttl

        entry = CacheEntry(
            query_hash=cache_key,
            query=query,
            response=response,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self._cache[cache_key] = entry
        self._stats.total_sets += 1
        self._stats.cache_size = len(self._cache)
        self._save_cache()
        return cache_key

    def invalidate(self, query: str) -> bool:
        """Remove a single entry from the cache."""
        cache_key = self.build_cache_key(query)
        return self.invalidate_by_key(cache_key)

    def invalidate_by_key(self, cache_key: str) -> bool:
        """Remove a single entry by pre-computed key."""
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._stats.total_invalidations += 1
            self._stats.cache_size = len(self._cache)
            self._save_cache()
            return True
        return False

    def invalidate_all(self) -> int:
        """Clear the whole cache and return the number of removed entries."""
        count = len(self._cache)
        self._cache.clear()
        self._stats.total_invalidations += count
        self._stats.cache_size = 0
        self._save_cache()
        return count

    def cleanup_expired(self) -> int:
        """Remove expired entries and return the count."""
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            self._stats.total_expired += len(expired_keys)
            self._stats.cache_size = len(self._cache)
            self._save_cache()
        return len(expired_keys)

    def get_stats(self) -> CacheStats:
        """Return current cache statistics."""
        self._stats.cache_size = len(self._cache)
        return self._stats

    def size(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)

    def clear(self) -> None:
        """Clear the cache and reset statistics."""
        self._cache.clear()
        self._stats = CacheStats()
        self._save_cache()

    def _save_cache(self) -> None:
        """Persist the cache to disk."""
        if not self.enable_persistence:
            return
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "entries": {
                    key: entry.model_dump()
                    for key, entry in self._cache.items()
                },
                "stats": self._stats.model_dump(),
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"Warning: response cache save failed: {exc}")

    def _load_cache(self) -> None:
        """Load the cache from disk."""
        if not self.enable_persistence:
            return
        if not self.cache_file.exists():
            return
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("entries", {})
            for key, entry_data in entries.items():
                self._cache[key] = CacheEntry(**entry_data)
            stats_data = data.get("stats", {})
            self._stats = CacheStats(**stats_data)
            self._stats.cache_size = len(self._cache)
        except Exception as exc:
            print(f"Warning: response cache load failed: {exc}")
            self._cache = {}
            self._stats = CacheStats()


# Global singleton used by the orchestrator and admin endpoints.
response_cache = ResponseCache()
