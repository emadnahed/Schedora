"""Unit tests for Redis client management."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from redis import Redis


class TestRedisClient:
    """Unit tests for Redis client singleton."""

    @patch('schedora.core.redis.Redis.from_url')
    def test_get_redis_creates_singleton(self, mock_from_url):
        """Test get_redis creates singleton instance."""
        from schedora.core.redis import get_redis, _redis_client
        from schedora.core import redis as redis_module

        # Reset global client
        redis_module._redis_client = None

        mock_client = Mock(spec=Redis)
        mock_from_url.return_value = mock_client

        client1 = get_redis()
        client2 = get_redis()

        # Should be same instance
        assert client1 is client2
        # Should only create once
        assert mock_from_url.call_count == 1

    @patch('schedora.core.redis.Redis.from_url')
    def test_get_redis_connection_reuse(self, mock_from_url):
        """Test Redis connection is reused across calls."""
        from schedora.core.redis import get_redis
        from schedora.core import redis as redis_module

        redis_module._redis_client = None

        mock_client = Mock(spec=Redis)
        mock_from_url.return_value = mock_client

        # Call multiple times
        for _ in range(5):
            get_redis()

        # Should only create once
        assert mock_from_url.call_count == 1

    @patch('schedora.core.redis.Redis.from_url')
    def test_close_redis(self, mock_from_url):
        """Test close_redis closes connection and clears singleton."""
        from schedora.core.redis import get_redis, close_redis
        from schedora.core import redis as redis_module

        redis_module._redis_client = None

        mock_client = Mock(spec=Redis)
        mock_from_url.return_value = mock_client

        client = get_redis()
        close_redis()

        # Should have called close
        mock_client.close.assert_called_once()

        # Should clear singleton
        assert redis_module._redis_client is None

    @patch('schedora.core.redis.Redis.from_url')
    def test_get_redis_with_config(self, mock_from_url):
        """Test get_redis uses config from settings."""
        from schedora.core.redis import get_redis
        from schedora.core import redis as redis_module

        redis_module._redis_client = None

        mock_client = Mock(spec=Redis)
        mock_from_url.return_value = mock_client

        get_redis()

        # Verify called with correct URL and params
        mock_from_url.assert_called_once()
        call_args = mock_from_url.call_args
        assert 'redis://localhost:6379/0' in str(call_args)
        assert call_args[1]['decode_responses'] is True


class TestAsyncRedisClient:
    """Unit tests for async Redis client singleton."""

    @pytest.mark.asyncio
    @patch('schedora.core.redis.AsyncRedis.from_url')
    async def test_get_async_redis_creates_singleton(self, mock_from_url):
        """Test get_async_redis creates singleton instance."""
        from schedora.core.redis import get_async_redis
        from schedora.core import redis as redis_module

        redis_module._async_redis_client = None

        mock_client = MagicMock()
        mock_from_url.return_value = mock_client

        client1 = await get_async_redis()
        client2 = await get_async_redis()

        # Should be same instance
        assert client1 is client2
        # Should only create once
        assert mock_from_url.call_count == 1

    @pytest.mark.asyncio
    @patch('schedora.core.redis.AsyncRedis.from_url')
    async def test_close_async_redis(self, mock_from_url):
        """Test close_async_redis closes connection."""
        from schedora.core.redis import get_async_redis, close_async_redis
        from schedora.core import redis as redis_module
        import asyncio

        redis_module._async_redis_client = None

        mock_client = MagicMock()
        # Make close() async-compatible
        async def async_close():
            pass
        mock_client.close = MagicMock(side_effect=async_close)
        mock_from_url.return_value = mock_client

        await get_async_redis()
        await close_async_redis()

        # Should have called close
        mock_client.close.assert_called_once()

        # Should clear singleton
        assert redis_module._async_redis_client is None
