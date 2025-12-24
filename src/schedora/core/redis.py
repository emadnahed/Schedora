"""Redis connection management for Schedora."""
from typing import Optional
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from schedora.config import get_settings

settings = get_settings()

# Synchronous Redis client (singleton)
_redis_client: Optional[Redis] = None

# Async Redis client (singleton)
_async_redis_client: Optional[AsyncRedis] = None


def get_redis() -> Redis:
    """
    Get synchronous Redis client (singleton).

    Returns:
        Redis: Synchronous Redis client instance

    Example:
        >>> redis = get_redis()
        >>> redis.set('key', 'value')
        >>> redis.get('key')
        'value'
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
    return _redis_client


async def get_async_redis() -> AsyncRedis:
    """
    Get async Redis client (singleton).

    Returns:
        AsyncRedis: Async Redis client instance

    Example:
        >>> redis = await get_async_redis()
        >>> await redis.set('key', 'value')
        >>> await redis.get('key')
        'value'
    """
    global _async_redis_client
    if _async_redis_client is None:
        _async_redis_client = AsyncRedis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
    return _async_redis_client


def close_redis() -> None:
    """
    Close synchronous Redis connection.

    Closes the connection and clears the singleton.
    Should be called on application shutdown.
    """
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None


async def close_async_redis() -> None:
    """
    Close async Redis connection.

    Closes the connection and clears the singleton.
    Should be called on application shutdown.
    """
    global _async_redis_client
    if _async_redis_client is not None:
        await _async_redis_client.close()
        _async_redis_client = None
