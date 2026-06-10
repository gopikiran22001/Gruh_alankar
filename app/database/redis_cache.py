"""
Gruha Alankara — Redis Cache Layer

Provides TTL-based caching, session management, rate limiting,
and JWT token blocklist support.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from config.constants import CACHE_TTL_SHORT, CACHE_TTL_MEDIUM, CACHE_TTL_SESSION
from config.logging_config import get_logger

logger = get_logger(__name__)


class RedisCache:
    """
    Redis-backed cache with typed helpers for common operations.
    Wraps the global redis_client from extensions.
    """

    _instance: Optional["RedisCache"] = None

    def __new__(cls) -> "RedisCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_client(self):
        """Get the Redis client lazily to avoid circular imports."""
        from app.extensions import redis_client
        if redis_client is None:
            raise RuntimeError("Redis is not connected.")
        return redis_client

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Basic Cache Operations
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get(self, key: str) -> Optional[str]:
        """Get a cached value by key."""
        try:
            return self._get_client().get(key)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None

    def set(self, key: str, value: str, ttl: int = CACHE_TTL_MEDIUM) -> bool:
        """Set a cached value with TTL."""
        try:
            return self._get_client().setex(key, ttl, value)
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))
            return False

    def delete(self, key: str) -> bool:
        """Delete a cached key."""
        try:
            return self._get_client().delete(key) > 0
        except Exception as e:
            logger.warning("cache_delete_failed", key=key, error=str(e))
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        try:
            return self._get_client().exists(key) > 0
        except Exception as e:
            logger.warning("cache_exists_failed", key=key, error=str(e))
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # JSON Cache Operations
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a JSON-serialized cached value."""
        raw = self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("cache_json_decode_failed", key=key)
        return None

    def set_json(self, key: str, value: Dict[str, Any], ttl: int = CACHE_TTL_MEDIUM) -> bool:
        """Set a JSON-serialized cached value."""
        try:
            return self.set(key, json.dumps(value, default=str), ttl)
        except Exception as e:
            logger.warning("cache_json_set_failed", key=key, error=str(e))
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Session Management
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def set_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Store session data with standard TTL."""
        key = f"session:{session_id}"
        return self.set_json(key, data, ttl=CACHE_TTL_SESSION)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data."""
        key = f"session:{session_id}"
        return self.get_json(key)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        key = f"session:{session_id}"
        return self.delete(key)

    def extend_session(self, session_id: str, ttl: int = CACHE_TTL_SESSION) -> bool:
        """Extend a session's TTL."""
        key = f"session:{session_id}"
        try:
            return self._get_client().expire(key, ttl)
        except Exception:
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Rate Limiting
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def check_rate_limit(
        self,
        identifier: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """
        Check and enforce rate limiting using sliding window counter.

        Args:
            identifier: Unique identifier (e.g., user_id, IP).
            max_requests: Maximum requests allowed in window.
            window_seconds: Window duration in seconds.

        Returns:
            Tuple of (allowed: bool, remaining: int).
        """
        key = f"ratelimit:{identifier}"
        try:
            client = self._get_client()
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            results = pipe.execute()

            current_count = results[0]
            ttl = results[1]

            # Set expiry on first request in window
            if ttl == -1:
                client.expire(key, window_seconds)

            remaining = max(0, max_requests - current_count)
            allowed = current_count <= max_requests

            return allowed, remaining
        except Exception as e:
            logger.warning("rate_limit_check_failed", identifier=identifier, error=str(e))
            # Fail open — allow the request if Redis is down
            return True, max_requests

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # JWT Token Blocklist
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def blocklist_token(self, jti: str, ttl: int = 3600) -> bool:
        """Add a JWT token ID to the blocklist."""
        key = f"jwt_blocklist:{jti}"
        return self.set(key, "1", ttl=ttl)

    def is_token_blocklisted(self, jti: str) -> bool:
        """Check if a JWT token ID is blocklisted."""
        key = f"jwt_blocklist:{jti}"
        return self.exists(key)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Workflow State Caching
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def cache_workflow_state(
        self,
        workflow_id: str,
        state: Dict[str, Any],
        ttl: int = CACHE_TTL_SHORT,
    ) -> bool:
        """Cache intermediate workflow state for status polling."""
        key = f"workflow:{workflow_id}"
        return self.set_json(key, state, ttl)

    def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached workflow state."""
        key = f"workflow:{workflow_id}"
        return self.get_json(key)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Agent Result Caching
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def cache_agent_result(
        self,
        agent_name: str,
        cache_key: str,
        result: Dict[str, Any],
        ttl: int = CACHE_TTL_MEDIUM,
    ) -> bool:
        """Cache an agent's result for deduplication."""
        key = f"agent_cache:{agent_name}:{cache_key}"
        return self.set_json(key, result, ttl)

    def get_cached_agent_result(
        self,
        agent_name: str,
        cache_key: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a cached agent result."""
        key = f"agent_cache:{agent_name}:{cache_key}"
        return self.get_json(key)


# Module-level singleton
cache = RedisCache()
