"""
Redis service for caching, token storage, and blacklisting.
"""
import json
from typing import Optional, Any
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import settings


class RedisService:
    """
    Redis service for managing cache, tokens, and blacklists.
    """

    _redis_client: Optional[Redis] = None

    @classmethod
    async def get_redis(cls) -> Redis:
        """
        Get or create Redis client instance.

        Returns:
            Redis client instance
        """
        if cls._redis_client is None:
            cls._redis_client = await redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                encoding="utf-8",
                decode_responses=True,
            )
        return cls._redis_client

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection."""
        if cls._redis_client:
            await cls._redis_client.close()
            cls._redis_client = None

    # Token Blacklist Methods
    @classmethod
    async def blacklist_token(cls, token: str, expires_in: int) -> bool:
        """
        Add a token to the blacklist.

        Args:
            token: JWT token to blacklist
            expires_in: Token expiration time in seconds

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        key = f"blacklist:token:{token}"
        await redis_client.setex(key, expires_in, "1")
        return True

    @classmethod
    async def is_token_blacklisted(cls, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted
        """
        redis_client = await cls.get_redis()
        key = f"blacklist:token:{token}"
        result = await redis_client.exists(key)
        return result > 0

    # Verification Token Methods
    @classmethod
    async def store_verification_token(
        cls, user_id: str, token: str, expires_in: int = 86400
    ) -> bool:
        """
        Store email verification token.

        Args:
            user_id: User's UUID as string
            token: Verification token
            expires_in: Expiration time in seconds (default: 24 hours)

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        key = f"verify:token:{token}"
        await redis_client.setex(key, expires_in, user_id)
        return True

    @classmethod
    async def get_verification_token(cls, token: str) -> Optional[str]:
        """
        Get user_id from verification token.

        Args:
            token: Verification token

        Returns:
            User ID if token exists, None otherwise
        """
        redis_client = await cls.get_redis()
        key = f"verify:token:{token}"
        user_id = await redis_client.get(key)
        return user_id

    @classmethod
    async def delete_verification_token(cls, token: str) -> bool:
        """
        Delete verification token after use.

        Args:
            token: Verification token

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        key = f"verify:token:{token}"
        await redis_client.delete(key)
        return True

    # Password Reset Token Methods
    @classmethod
    async def store_reset_token(
        cls, user_id: str, token: str, expires_in: int = 3600
    ) -> bool:
        """
        Store password reset token.

        Args:
            user_id: User's UUID as string
            token: Reset token
            expires_in: Expiration time in seconds (default: 1 hour)

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        key = f"reset:token:{token}"
        await redis_client.setex(key, expires_in, user_id)
        return True

    @classmethod
    async def get_reset_token(cls, token: str) -> Optional[str]:
        """
        Get user_id from reset token.

        Args:
            token: Reset token

        Returns:
            User ID if token exists, None otherwise
        """
        redis_client = await cls.get_redis()
        key = f"reset:token:{token}"
        user_id = await redis_client.get(key)
        return user_id

    @classmethod
    async def delete_reset_token(cls, token: str) -> bool:
        """
        Delete reset token after use.

        Args:
            token: Reset token

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        key = f"reset:token:{token}"
        await redis_client.delete(key)
        return True

    # Rate Limiting Methods
    @classmethod
    async def check_rate_limit(
        cls, identifier: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded.

        Args:
            identifier: Unique identifier (user_id, api_key, IP, etc.)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        redis_client = await cls.get_redis()
        key = f"ratelimit:{identifier}"

        # Increment counter
        current = await redis_client.incr(key)

        # Set expiration on first request
        if current == 1:
            await redis_client.expire(key, window_seconds)

        # Check if limit exceeded
        is_allowed = current <= max_requests
        remaining = max(0, max_requests - current)

        return is_allowed, remaining

    @classmethod
    async def reset_rate_limit(cls, identifier: str) -> bool:
        """
        Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        key = f"ratelimit:{identifier}"
        await redis_client.delete(key)
        return True

    # API Key Usage Tracking
    @classmethod
    async def track_api_usage(cls, api_key: str, endpoint: str) -> bool:
        """
        Track API key usage for analytics.

        Args:
            api_key: API key
            endpoint: API endpoint accessed

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        key = f"api:usage:{api_key}:{endpoint}"
        await redis_client.incr(key)
        # Set expiration to 30 days for analytics
        await redis_client.expire(key, 30 * 24 * 60 * 60)
        return True

    @classmethod
    async def get_api_usage(cls, api_key: str) -> dict:
        """
        Get API usage statistics for an API key.

        Args:
            api_key: API key

        Returns:
            Dictionary of endpoint usage counts
        """
        redis_client = await cls.get_redis()
        pattern = f"api:usage:{api_key}:*"
        keys = await redis_client.keys(pattern)

        usage = {}
        for key in keys:
            endpoint = key.split(":", 3)[3]  # Extract endpoint from key
            count = await redis_client.get(key)
            usage[endpoint] = int(count) if count else 0

        return usage

    # Generic Cache Methods
    @classmethod
    async def set_cache(
        cls, key: str, value: Any, expires_in: Optional[int] = None
    ) -> bool:
        """
        Set a cache value.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            expires_in: Optional expiration in seconds

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        serialized_value = json.dumps(value)

        if expires_in:
            await redis_client.setex(key, expires_in, serialized_value)
        else:
            await redis_client.set(key, serialized_value)

        return True

    @classmethod
    async def get_cache(cls, key: str) -> Optional[Any]:
        """
        Get a cache value.

        Args:
            key: Cache key

        Returns:
            Cached value (JSON deserialized) or None
        """
        redis_client = await cls.get_redis()
        value = await redis_client.get(key)

        if value:
            return json.loads(value)
        return None

    @classmethod
    async def delete_cache(cls, key: str) -> bool:
        """
        Delete a cache value.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        redis_client = await cls.get_redis()
        await redis_client.delete(key)
        return True

    @classmethod
    async def exists(cls, key: str) -> bool:
        """
        Check if a key exists.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        redis_client = await cls.get_redis()
        result = await redis_client.exists(key)
        return result > 0


# Singleton instance for app lifecycle
redis_service = RedisService()
