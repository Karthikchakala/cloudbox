import os
import json
import logging
import redis
from typing import Any, Optional

logger = logging.getLogger("cloudbox.cache")

class CacheService:
    """
    Resilient Redis Caching Service.
    Provides JSON caching, user-segregated keys, and graceful fallback to DB if Redis is unavailable.
    """

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connected: bool = False
        self._hits: int = 0
        self._misses: int = 0
        self._init_client()

    def _init_client(self):
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", None) or None
        redis_db = int(os.getenv("REDIS_DB", 0))

        try:
            pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=True
            )
            self.client = redis.Redis(connection_pool=pool)
            # Verify connectivity
            self.client.ping()
            self._connected = True
            logger.info(f"[*] Redis cache connected successfully to {redis_host}:{redis_port}/{redis_db}")
        except Exception as e:
            logger.warning(f"[*] Notice: Redis unavailable ({e}). Running in DB-fallback cache mode.")
            self._connected = False

    @property
    def is_available(self) -> bool:
        if not self.client:
            return False
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def get_json(self, key: str) -> Optional[Any]:
        """Retrieve and parse JSON object from cache."""
        if not self.client:
            self._misses += 1
            return None
        try:
            val = self.client.get(key)
            if val is not None:
                self._hits += 1
                return json.loads(val)
            self._misses += 1
            return None
        except Exception as e:
            logger.debug(f"Cache GET error for key '{key}': {e}")
            self._misses += 1
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Store a JSON serializable value with TTL expiration."""
        if not self.client:
            return False
        try:
            serialized = json.dumps(value)
            return bool(self.client.setex(key, ttl_seconds, serialized))
        except Exception as e:
            logger.debug(f"Cache SET error for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a single cache key."""
        if not self.client:
            return False
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.debug(f"Cache DELETE error for key '{key}': {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching the specified pattern (e.g. user:123:*)."""
        if not self.client:
            return 0
        try:
            keys = list(self.client.scan_iter(match=pattern, count=100))
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.debug(f"Cache DELETE_PATTERN error for '{pattern}': {e}")
            return 0

    def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cached listings and analytics for a specific user."""
        return self.delete_pattern(f"user:{user_id}:*")

    def invalidate_file_cache(self, file_id: str) -> int:
        """Invalidate file metadata and version cache for a specific file."""
        return self.delete_pattern(f"file:{file_id}:*")

    def get_stats(self) -> dict:
        """Return operational cache telemetry."""
        total_reqs = self._hits + self._misses
        hit_ratio = round((self._hits / total_reqs * 100), 2) if total_reqs > 0 else 0.0
        return {
            "connected": self.is_available,
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_reqs,
            "hit_ratio_percent": hit_ratio,
        }

cache_service = CacheService()
