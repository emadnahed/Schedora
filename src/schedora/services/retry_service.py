"""Retry service for calculating backoff delays."""
import random
from datetime import datetime, timedelta, timezone
from schedora.core.enums import RetryPolicy


class RetryService:
    """Service for retry backoff calculations."""

    def calculate_next_retry(
        self,
        retry_count: int,
        max_retries: int,
        retry_policy: RetryPolicy,
        base_delay: int = 60,
        max_delay: int = 3600,
    ) -> datetime:
        """
        Calculate next retry time based on retry policy.

        Args:
            retry_count: Current retry attempt number
            max_retries: Maximum retry attempts allowed
            retry_policy: Retry backoff policy (fixed, exponential, jitter)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds (for exponential)

        Returns:
            datetime: Next scheduled retry time
        """
        if retry_policy == RetryPolicy.FIXED:
            delay = base_delay

        elif retry_policy == RetryPolicy.EXPONENTIAL:
            # Exponential backoff: base_delay * 2^retry_count
            delay = base_delay * (2 ** retry_count)
            # Cap at max_delay
            delay = min(delay, max_delay)

        elif retry_policy == RetryPolicy.JITTER:
            # Exponential with jitter: base_delay * 2^retry_count + random
            exponential_delay = base_delay * (2 ** retry_count)
            exponential_delay = min(exponential_delay, max_delay)
            # Add random jitter (0 to 50% of exponential delay)
            jitter = random.uniform(0, exponential_delay * 0.5)
            delay = exponential_delay + jitter

        else:
            delay = base_delay

        return datetime.now(timezone.utc) + timedelta(seconds=delay)

    def should_retry(self, retry_count: int, max_retries: int) -> bool:
        """
        Check if job should be retried.

        Args:
            retry_count: Current retry attempt number
            max_retries: Maximum retry attempts allowed

        Returns:
            bool: True if should retry, False otherwise
        """
        return retry_count < max_retries
