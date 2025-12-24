"""Integration tests for Redis connectivity and operations."""
import pytest
from datetime import datetime


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests for Redis operations."""

    def test_redis_connectivity(self):
        """Test Redis connection works."""
        from schedora.core.redis import get_redis

        redis = get_redis()

        # Test ping
        assert redis.ping() is True

    def test_redis_set_get(self):
        """Test basic set and get operations."""
        from schedora.core.redis import get_redis

        redis = get_redis()

        # Set and get value
        redis.set('test_key', 'test_value')
        value = redis.get('test_key')

        assert value == 'test_value'

        # Cleanup
        redis.delete('test_key')

    def test_redis_ttl(self):
        """Test TTL (time-to-live) operations."""
        from schedora.core.redis import get_redis

        redis = get_redis()

        # Set key with TTL
        redis.setex('ttl_test', 10, 'value')

        # Check TTL exists
        ttl = redis.ttl('ttl_test')
        assert ttl > 0
        assert ttl <= 10

        # Cleanup
        redis.delete('ttl_test')

    def test_redis_delete(self):
        """Test delete operation."""
        from schedora.core.redis import get_redis

        redis = get_redis()

        # Set and delete
        redis.set('delete_test', 'value')
        assert redis.exists('delete_test') == 1

        redis.delete('delete_test')
        assert redis.exists('delete_test') == 0

    def test_redis_hash_operations(self):
        """Test hash operations (HSET, HGET, HGETALL)."""
        from schedora.core.redis import get_redis

        redis = get_redis()

        # Set hash fields
        redis.hset('test_hash', 'field1', 'value1')
        redis.hset('test_hash', 'field2', 'value2')

        # Get single field
        value = redis.hget('test_hash', 'field1')
        assert value == 'value1'

        # Get all fields
        all_values = redis.hgetall('test_hash')
        assert all_values == {'field1': 'value1', 'field2': 'value2'}

        # Cleanup
        redis.delete('test_hash')

    def test_redis_set_operations(self):
        """Test set operations (SADD, SMEMBERS, SREM)."""
        from schedora.core.redis import get_redis

        redis = get_redis()

        # Add to set
        redis.sadd('test_set', 'member1', 'member2', 'member3')

        # Get members
        members = redis.smembers('test_set')
        assert members == {'member1', 'member2', 'member3'}

        # Remove member
        redis.srem('test_set', 'member2')
        members = redis.smembers('test_set')
        assert members == {'member1', 'member3'}

        # Cleanup
        redis.delete('test_set')

    def test_redis_test_isolation(self):
        """Test that tests are isolated (no key pollution)."""
        from schedora.core.redis import get_redis

        redis = get_redis()

        # Keys from this test should not exist
        assert redis.exists('test_key') == 0
        assert redis.exists('ttl_test') == 0
        assert redis.exists('delete_test') == 0


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncRedisIntegration:
    """Integration tests for async Redis operations."""

    async def test_async_redis_connectivity(self):
        """Test async Redis connection works."""
        from schedora.core.redis import get_async_redis

        redis = await get_async_redis()

        # Test ping
        result = await redis.ping()
        assert result is True

    async def test_async_redis_set_get(self):
        """Test async set and get operations."""
        from schedora.core.redis import get_async_redis

        redis = await get_async_redis()

        # Set and get value
        await redis.set('async_test_key', 'async_value')
        value = await redis.get('async_test_key')

        assert value == 'async_value'

        # Cleanup
        await redis.delete('async_test_key')

    async def test_async_redis_ttl(self):
        """Test async TTL operations."""
        from schedora.core.redis import get_async_redis

        redis = await get_async_redis()

        # Set key with TTL
        await redis.setex('async_ttl_test', 10, 'value')

        # Check TTL exists
        ttl = await redis.ttl('async_ttl_test')
        assert ttl > 0
        assert ttl <= 10

        # Cleanup
        await redis.delete('async_ttl_test')
