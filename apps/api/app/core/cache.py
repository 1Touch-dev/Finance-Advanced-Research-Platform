"""
Redis cache client — used for session storage and data caching.

Falls back gracefully to in-memory dict when Redis is unavailable.
"""
import os
import json
import logging
from typing import Optional, Any

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

_client = None
_fallback: dict = {}


def get_redis():
    """Get Redis client, or None if unavailable."""
    global _client
    if _client is not None:
        return _client
    try:
        import redis
        _client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2)
        _client.ping()
        log.info({"event": "redis_connected", "url": REDIS_URL.split("@")[-1]})
        return _client
    except Exception as e:
        log.warning({"event": "redis_unavailable", "error": str(e)[:100]})
        _client = None
        return None


def cache_get(key: str) -> Optional[str]:
    """Get a value from Redis cache (falls back to in-memory)."""
    r = get_redis()
    if r:
        try:
            return r.get(key)
        except Exception:
            pass
    return _fallback.get(key)


def cache_set(key: str, value: str, ttl: int = 3600):
    """Set a value in Redis cache with TTL (falls back to in-memory)."""
    r = get_redis()
    if r:
        try:
            r.setex(key, ttl, value)
            return
        except Exception:
            pass
    _fallback[key] = value


def cache_json_get(key: str) -> Optional[Any]:
    """Get and deserialize JSON from cache."""
    raw = cache_get(key)
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def cache_json_set(key: str, data: Any, ttl: int = 3600):
    """Serialize and cache JSON data."""
    cache_set(key, json.dumps(data, default=str), ttl)


def cache_delete(key: str):
    """Delete a cache key."""
    r = get_redis()
    if r:
        try:
            r.delete(key)
        except Exception:
            pass
    _fallback.pop(key, None)


def get_cache_stats() -> dict:
    """Get cache health info."""
    r = get_redis()
    if r:
        try:
            info = r.info("memory")
            return {
                "backend": "redis",
                "connected": True,
                "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "keys": r.dbsize(),
            }
        except Exception as e:
            return {"backend": "redis", "connected": False, "error": str(e)[:100]}
    return {"backend": "memory", "connected": False, "keys": len(_fallback)}
