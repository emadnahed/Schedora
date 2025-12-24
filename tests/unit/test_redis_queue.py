"""Unit tests for Redis queue service."""
import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock


class TestRedisQueue:
    """Test RedisQueue service."""

    def test_enqueue_job(self):
        """Test enqueuing a job to Redis."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        queue = RedisQueue(mock_redis)

        job_id = uuid4()
        queue.enqueue(job_id, priority=5)

        # Verify zadd was called with correct arguments
        mock_redis.zadd.assert_called_once()
        call_args = mock_redis.zadd.call_args
        assert call_args[0][0] == "schedora:queue:jobs"  # queue name
        assert str(job_id) in call_args[0][1]  # job_id in mapping
        assert call_args[0][1][str(job_id)] == 5  # priority

    def test_enqueue_with_default_priority(self):
        """Test enqueuing with default priority (0)."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        queue = RedisQueue(mock_redis)

        job_id = uuid4()
        queue.enqueue(job_id)  # No priority specified

        call_args = mock_redis.zadd.call_args
        assert call_args[0][1][str(job_id)] == 0

    def test_dequeue_job(self):
        """Test dequeuing highest priority job."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        job_id = uuid4()
        mock_redis.zpopmax.return_value = [(str(job_id), 10)]  # (member, score)

        queue = RedisQueue(mock_redis)
        result = queue.dequeue()

        assert result == job_id
        mock_redis.zpopmax.assert_called_once_with("schedora:queue:jobs", count=1)

    def test_dequeue_empty_queue(self):
        """Test dequeuing from empty queue returns None."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        mock_redis.zpopmax.return_value = []  # Empty queue

        queue = RedisQueue(mock_redis)
        result = queue.dequeue()

        assert result is None

    def test_get_queue_length(self):
        """Test getting queue length."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        mock_redis.zcard.return_value = 42

        queue = RedisQueue(mock_redis)
        length = queue.get_queue_length()

        assert length == 42
        mock_redis.zcard.assert_called_once_with("schedora:queue:jobs")

    def test_move_to_dlq(self):
        """Test moving job to dead letter queue."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        mock_redis.zrem.return_value = 1  # Job found and removed
        queue = RedisQueue(mock_redis)

        job_id = uuid4()
        queue.move_to_dlq(job_id, "Max retries exceeded")

        # Verify job added to DLQ with metadata
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert "schedora:queue:jobs:dlq" in call_args[0]
        assert str(job_id) in call_args[0]

    def test_get_dlq_length(self):
        """Test getting dead letter queue length."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        mock_redis.hlen.return_value = 5

        queue = RedisQueue(mock_redis)
        length = queue.get_dlq_length()

        assert length == 5
        mock_redis.hlen.assert_called_once_with("schedora:queue:jobs:dlq")

    def test_custom_queue_name(self):
        """Test using custom queue name."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        queue = RedisQueue(mock_redis, queue_name="custom_queue")

        job_id = uuid4()
        queue.enqueue(job_id)

        call_args = mock_redis.zadd.call_args
        assert call_args[0][0] == "schedora:queue:custom_queue"

    def test_peek_next_job(self):
        """Test peeking at next job without removing it."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        job_id = uuid4()
        mock_redis.zrange.return_value = [(str(job_id), 10)]

        queue = RedisQueue(mock_redis)
        result = queue.peek()

        assert result == job_id
        # Verify it was peek, not pop
        mock_redis.zrange.assert_called_once()
        mock_redis.zpopmax.assert_not_called()

    def test_remove_specific_job(self):
        """Test removing a specific job from queue."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        mock_redis.zrem.return_value = 1  # 1 member removed

        queue = RedisQueue(mock_redis)
        job_id = uuid4()
        removed = queue.remove(job_id)

        assert removed is True
        mock_redis.zrem.assert_called_once_with("schedora:queue:jobs", str(job_id))

    def test_purge_queue(self):
        """Test purging all jobs from queue."""
        from schedora.services.redis_queue import RedisQueue

        mock_redis = Mock()
        queue = RedisQueue(mock_redis)

        queue.purge()

        mock_redis.delete.assert_called_once_with("schedora:queue:jobs")
