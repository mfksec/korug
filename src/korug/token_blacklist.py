"""Token revocation store, keyed by JWT id (jti).

Supports two backends:

* **Redis** (when ``REDIS_URL`` is configured) - shared across all worker
  processes and durable across restarts. This is required for correct logout /
  revocation behaviour in a multi-worker production deployment.
* **In-memory** (fallback) - thread-safe per-process dict, used for local
  single-process development and tests. Not shared across workers.

Tokens are tracked by their ``jti`` claim (a short random id) rather than the
full token string: it is smaller, constant-length, and never leaks the bearer
token into the store.
"""
from datetime import datetime, timezone
from typing import Dict, Optional
import logging
import threading

from korug.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_KEY_PREFIX = "revoked_jti:"

# In-memory fallback: jti -> expiry timestamp (epoch seconds)
_blacklist: Dict[str, float] = {}
_lock = threading.Lock()

# Lazily-initialised Redis client (None when Redis is not configured).
_redis_client = None
_redis_init_attempted = False


def _get_redis():
    """Return a Redis client if configured and reachable, else None."""
    global _redis_client, _redis_init_attempted
    if _redis_init_attempted:
        return _redis_client
    _redis_init_attempted = True
    if not settings.redis_url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=5
        )
        client.ping()
        _redis_client = client
        logger.info("Token revocation store: using Redis")
    except Exception as e:  # pragma: no cover - depends on runtime environment
        logger.error(
            "Redis configured but unavailable (%s); falling back to in-memory "
            "revocation store. Revocation will NOT be shared across workers.",
            e,
        )
        _redis_client = None
    return _redis_client


def add_to_blacklist(jti: str, expires_at: datetime) -> None:
    """Revoke a token by its jti until its natural expiry.

    Args:
        jti: The JWT id claim of the token to revoke.
        expires_at: Token expiration time; the entry auto-expires at this point.
    """
    if not jti:
        return
    client = _get_redis()
    if client is not None:
        # TTL in seconds until the token would expire anyway; nothing to store
        # once the token is no longer valid.
        ttl = int(expires_at.timestamp() - datetime.now(timezone.utc).timestamp())
        if ttl <= 0:
            return
        try:
            client.setex(_KEY_PREFIX + jti, ttl, "1")
            return
        except Exception as e:  # pragma: no cover
            logger.error("Redis revocation write failed (%s); using in-memory", e)
    with _lock:
        _blacklist[jti] = expires_at.timestamp()


def is_blacklisted(jti: Optional[str]) -> bool:
    """Return True if the given jti has been revoked."""
    if not jti:
        return False
    client = _get_redis()
    if client is not None:
        try:
            return client.exists(_KEY_PREFIX + jti) == 1
        except Exception as e:  # pragma: no cover
            logger.error("Redis revocation read failed (%s); using in-memory", e)
    with _lock:
        expiration = _blacklist.get(jti)
        if expiration is None:
            return False
        if datetime.now(timezone.utc).timestamp() > expiration:
            del _blacklist[jti]
            return False
        return True


def clear_blacklist() -> None:
    """Clear the in-memory revocation store (used by tests)."""
    with _lock:
        _blacklist.clear()


def cleanup_expired_tokens() -> int:
    """Remove expired entries from the in-memory store. Returns count removed.

    Redis entries expire automatically via TTL, so this only affects the
    in-memory fallback.
    """
    with _lock:
        now = datetime.now(timezone.utc).timestamp()
        expired = [jti for jti, exp_time in _blacklist.items() if now > exp_time]
        for jti in expired:
            del _blacklist[jti]
        return len(expired)


def get_blacklist_stats() -> Dict[str, int]:
    """Return in-memory revocation store statistics for monitoring."""
    with _lock:
        now = datetime.now(timezone.utc).timestamp()
        expired_count = sum(1 for exp_time in _blacklist.values() if now > exp_time)
        return {
            "total_blacklisted": len(_blacklist),
            "expired_entries": expired_count,
            "active_entries": len(_blacklist) - expired_count,
        }
