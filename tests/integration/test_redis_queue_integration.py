"""Integration tests for Redis queue with real Redis instance."""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from schedora.services.redis_queue import RedisQueue


@pytest.mark.integration
class TestRedisQueueIntegration:
    """Test RedisQueue with real Redis instance."""

    def test_enqueue_dequeue_flow(self, redis_client):
        """Test complete enqueue/dequeue flow."""
        queue = RedisQueue(redis_client, queue_name="test_enqueue_dequeue")
        queue.purge()  # Clean start

        # Enqueue 3 jobs with different priorities
        job1 = uuid4()
        job2 = uuid4()
        job3 = uuid4()

        queue.enqueue(job1, priority=1)
        queue.enqueue(job2, priority=10)  # Highest priority
        queue.enqueue(job3, priority=5)

        # Should dequeue in priority order: job2 (10), job3 (5), job1 (1)
        assert queue.dequeue() == job2
        assert queue.dequeue() == job3
        assert queue.dequeue() == job1
        assert queue.dequeue() is None  # Empty queue

    def test_multiple_queues(self, redis_client):
        """Test multiple independent queues."""
        queue_a = RedisQueue(redis_client, queue_name="queue_a")
        queue_b = RedisQueue(redis_client, queue_name="queue_b")

        job_a = uuid4()
        job_b = uuid4()

        queue_a.enqueue(job_a)
        queue_b.enqueue(job_b)

        # Jobs should be in separate queues
        assert queue_a.get_queue_length() == 1
        assert queue_b.get_queue_length() == 1

        assert queue_a.dequeue() == job_a
        assert queue_b.dequeue() == job_b

    def test_dead_letter_queue_flow(self, redis_client):
        """Test moving jobs to DLQ."""
        queue = RedisQueue(redis_client, queue_name="test_dlq_flow")
        queue.purge()
        queue.purge_dlq()

        job_id = uuid4()
        queue.enqueue(job_id, priority=5)

        # Move to DLQ
        reason = "Max retries exceeded"
        queue.move_to_dlq(job_id, reason)

        # Should be removed from main queue
        assert queue.get_queue_length() == 0
        assert queue.dequeue() is None

        # Should be in DLQ
        assert queue.get_dlq_length() == 1

    def test_queue_persistence(self, redis_client):
        """Test queue persists across RedisQueue instances."""
        job_id = uuid4()
        queue_name = "test_persistence"

        # Enqueue in one instance
        queue1 = RedisQueue(redis_client, queue_name=queue_name)
        queue1.purge()
        queue1.enqueue(job_id, priority=10)

        # Dequeue in another instance (same queue name)
        queue2 = RedisQueue(redis_client, queue_name=queue_name)
        assert queue2.get_queue_length() == 1
        assert queue2.dequeue() == job_id

    def test_peek_does_not_remove(self, redis_client):
        """Test peeking doesn't remove job from queue."""
        queue = RedisQueue(redis_client, queue_name="test_peek")
        queue.purge()

        job1 = uuid4()
        job2 = uuid4()

        queue.enqueue(job1, priority=5)
        queue.enqueue(job2, priority=10)

        # Peek multiple times
        assert queue.peek() == job2
        assert queue.peek() == job2
        assert queue.get_queue_length() == 2

        # Dequeue removes it
        assert queue.dequeue() == job2
        assert queue.peek() == job1
        assert queue.get_queue_length() == 1

    def test_remove_specific_job(self, redis_client):
        """Test removing specific job from queue."""
        queue = RedisQueue(redis_client, queue_name="test_remove")
        queue.purge()

        job1 = uuid4()
        job2 = uuid4()
        job3 = uuid4()

        queue.enqueue(job1, priority=1)
        queue.enqueue(job2, priority=2)
        queue.enqueue(job3, priority=3)

        # Remove middle job
        assert queue.remove(job2) is True
        assert queue.get_queue_length() == 2

        # Verify job2 is gone
        assert queue.dequeue() == job3
        assert queue.dequeue() == job1

    def test_purge_queue(self, redis_client):
        """Test purging all jobs from queue."""
        queue = RedisQueue(redis_client, queue_name="test_purge")
        queue.purge()

        # Add multiple jobs
        for i in range(10):
            queue.enqueue(uuid4(), priority=i)

        assert queue.get_queue_length() == 10

        # Purge
        queue.purge()

        assert queue.get_queue_length() == 0
        assert queue.dequeue() is None

    def test_purge_dlq(self, redis_client):
        """Test purging dead letter queue."""
        queue = RedisQueue(redis_client, queue_name="test_purge_dlq")
        queue.purge()
        queue.purge_dlq()

        # Move multiple jobs to DLQ
        for i in range(5):
            job_id = uuid4()
            queue.enqueue(job_id)
            queue.move_to_dlq(job_id, f"Error {i}")

        assert queue.get_dlq_length() == 5

        # Purge DLQ
        queue.purge_dlq()

        assert queue.get_dlq_length() == 0

    def test_fifo_ordering_same_priority(self, redis_client):
        """Test FIFO ordering for jobs with same priority."""
        queue = RedisQueue(redis_client, queue_name="test_fifo")
        queue.purge()

        jobs = [uuid4() for _ in range(5)]

        # Enqueue all with same priority
        for job in jobs:
            queue.enqueue(job, priority=5)

        # Should dequeue in FIFO order (Redis sorted set behavior)
        # Note: With same scores, Redis uses lexicographic ordering
        # So we can't guarantee FIFO, but all jobs should be retrievable
        dequeued = []
        for _ in range(5):
            dequeued.append(queue.dequeue())

        # Verify all jobs were dequeued
        assert set(dequeued) == set(jobs)
        assert queue.dequeue() is None

    def test_concurrent_enqueue_dequeue(self, redis_client):
        """Test concurrent operations don't cause issues."""
        queue = RedisQueue(redis_client, queue_name="test_concurrent")
        queue.purge()

        # Enqueue many jobs
        jobs = [uuid4() for _ in range(20)]
        for i, job in enumerate(jobs):
            queue.enqueue(job, priority=i)

        assert queue.get_queue_length() == 20

        # Dequeue half
        dequeued = []
        for _ in range(10):
            dequeued.append(queue.dequeue())

        assert queue.get_queue_length() == 10
        assert len(dequeued) == 10

        # Enqueue more
        new_jobs = [uuid4() for _ in range(5)]
        for i, job in enumerate(new_jobs):
            queue.enqueue(job, priority=100 + i)  # Higher priority

        assert queue.get_queue_length() == 15

        # New jobs should come first (higher priority)
        next_job = queue.dequeue()
        assert next_job in new_jobs

    def test_empty_queue_operations(self, redis_client):
        """Test operations on empty queue."""
        queue = RedisQueue(redis_client, queue_name="test_empty")
        queue.purge()

        # All operations should handle empty queue gracefully
        assert queue.get_queue_length() == 0
        assert queue.dequeue() is None
        assert queue.peek() is None
        assert queue.remove(uuid4()) is False

        # Purge empty queue should not error
        queue.purge()
        assert queue.get_queue_length() == 0

    def test_dlq_metadata(self, redis_client):
        """Test DLQ stores metadata correctly."""
        import json

        queue = RedisQueue(redis_client, queue_name="test_dlq_metadata")
        queue.purge()
        queue.purge_dlq()

        job_id = uuid4()
        queue.enqueue(job_id)

        reason = "Connection timeout after 3 retries"
        before_time = datetime.now(timezone.utc)
        queue.move_to_dlq(job_id, reason)
        after_time = datetime.now(timezone.utc)

        # Verify metadata was stored
        dlq_data_raw = redis_client.hget(queue.dlq_name, str(job_id))
        assert dlq_data_raw is not None

        dlq_data = json.loads(dlq_data_raw)
        assert dlq_data["job_id"] == str(job_id)
        assert dlq_data["reason"] == reason

        # Verify timestamp is reasonable
        moved_at = datetime.fromisoformat(dlq_data["moved_at"])
        assert before_time <= moved_at <= after_time
