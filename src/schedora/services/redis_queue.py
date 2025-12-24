"""Redis-based job queue for scalable job distribution."""
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from redis import Redis


class RedisQueue:
    """
    Redis-based priority queue for jobs.

    Uses Redis sorted sets for priority queue functionality.
    Higher priority values are dequeued first.
    """

    def __init__(self, redis: Redis, queue_name: str = "jobs"):
        """
        Initialize Redis queue.

        Args:
            redis: Redis client instance
            queue_name: Name of the queue (default: "jobs")
        """
        self.redis = redis
        self.queue_name = f"schedora:queue:{queue_name}"
        self.dlq_name = f"{self.queue_name}:dlq"

    def enqueue(self, job_id: UUID, priority: int = 0) -> None:
        """
        Add job to queue with priority.

        Args:
            job_id: Job UUID
            priority: Job priority (higher = processed first, default: 0)
        """
        # Use sorted set with priority as score
        # Higher scores are processed first (ZPOPMAX)
        self.redis.zadd(self.queue_name, {str(job_id): priority})

    def dequeue(self) -> Optional[UUID]:
        """
        Remove and return highest priority job from queue.

        Returns:
            Optional[UUID]: Job ID if available, None if queue empty
        """
        # ZPOPMAX returns highest score (highest priority)
        result = self.redis.zpopmax(self.queue_name, count=1)

        if result:
            job_id_str, _priority = result[0]
            return UUID(job_id_str)
        return None

    def peek(self) -> Optional[UUID]:
        """
        View highest priority job without removing it.

        Returns:
            Optional[UUID]: Job ID if available, None if queue empty
        """
        # ZRANGE with DESC to get highest priority (first element when sorted desc)
        result = self.redis.zrange(
            self.queue_name,
            0,  # First element (highest score when desc=True)
            0,  # First element
            withscores=True,
            desc=True
        )

        if result:
            job_id_str, _priority = result[0]
            return UUID(job_id_str)
        return None

    def remove(self, job_id: UUID) -> bool:
        """
        Remove a specific job from the queue.

        Args:
            job_id: Job UUID to remove

        Returns:
            bool: True if job was removed, False if not found
        """
        removed = self.redis.zrem(self.queue_name, str(job_id))
        return removed > 0

    def get_queue_length(self) -> int:
        """
        Get number of jobs in queue.

        Returns:
            int: Number of jobs in queue
        """
        return self.redis.zcard(self.queue_name)

    def move_to_dlq(self, job_id: UUID, reason: str) -> None:
        """
        Move failed job to dead letter queue.

        Args:
            job_id: Job UUID
            reason: Failure reason
        """
        # Store job with failure metadata in hash
        dlq_data = json.dumps({
            "job_id": str(job_id),
            "reason": reason,
            "moved_at": datetime.now(timezone.utc).isoformat(),
        })

        self.redis.hset(self.dlq_name, str(job_id), dlq_data)

        # Remove from main queue if present
        self.remove(job_id)

    def get_dlq_length(self) -> int:
        """
        Get number of jobs in dead letter queue.

        Returns:
            int: Number of jobs in DLQ
        """
        return self.redis.hlen(self.dlq_name)

    def purge(self) -> None:
        """Delete all jobs from the queue."""
        self.redis.delete(self.queue_name)

    def purge_dlq(self) -> None:
        """Delete all jobs from the dead letter queue."""
        self.redis.delete(self.dlq_name)
