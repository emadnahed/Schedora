"""Unit tests for retry backoff calculations."""
import pytest
from datetime import datetime, timedelta, timezone
from schedora.services.retry_service import RetryService
from schedora.core.enums import RetryPolicy


class TestRetryService:
    """Test retry backoff calculations."""

    def test_fixed_backoff_60_seconds(self):
        """Test fixed backoff returns constant delay."""
        service = RetryService()

        next_retry = service.calculate_next_retry(
            retry_count=1,
            max_retries=3,
            retry_policy=RetryPolicy.FIXED,
            base_delay=60,
        )

        # Should be ~60 seconds from now
        expected = datetime.now(timezone.utc) + timedelta(seconds=60)
        assert abs((next_retry - expected).total_seconds()) < 2  # Within 2 seconds

    def test_fixed_backoff_multiple_retries(self):
        """Test fixed backoff is same regardless of retry count."""
        service = RetryService()

        retry1 = service.calculate_next_retry(
            retry_count=1, max_retries=5, retry_policy=RetryPolicy.FIXED, base_delay=30
        )
        retry3 = service.calculate_next_retry(
            retry_count=3, max_retries=5, retry_policy=RetryPolicy.FIXED, base_delay=30
        )

        # Both should be ~30 seconds from their calculation time
        now = datetime.now(timezone.utc)
        assert abs((retry1 - now - timedelta(seconds=30)).total_seconds()) < 2
        assert abs((retry3 - now - timedelta(seconds=30)).total_seconds()) < 2

    def test_exponential_backoff_increases(self):
        """Test exponential backoff increases with retry count."""
        service = RetryService()

        retry1 = service.calculate_next_retry(
            retry_count=1, max_retries=5, retry_policy=RetryPolicy.EXPONENTIAL, base_delay=10
        )
        retry2 = service.calculate_next_retry(
            retry_count=2, max_retries=5, retry_policy=RetryPolicy.EXPONENTIAL, base_delay=10
        )
        retry3 = service.calculate_next_retry(
            retry_count=3, max_retries=5, retry_policy=RetryPolicy.EXPONENTIAL, base_delay=10
        )

        now = datetime.now(timezone.utc)

        # Exponential: 10 * 2^1 = 20, 10 * 2^2 = 40, 10 * 2^3 = 80
        delay1 = (retry1 - now).total_seconds()
        delay2 = (retry2 - now).total_seconds()
        delay3 = (retry3 - now).total_seconds()

        assert 18 <= delay1 <= 22  # ~20 seconds
        assert 38 <= delay2 <= 42  # ~40 seconds
        assert 78 <= delay3 <= 82  # ~80 seconds

    def test_exponential_backoff_with_max_delay(self):
        """Test exponential backoff respects max delay."""
        service = RetryService()

        retry5 = service.calculate_next_retry(
            retry_count=5,
            max_retries=10,
            retry_policy=RetryPolicy.EXPONENTIAL,
            base_delay=10,
            max_delay=100,
        )

        now = datetime.now(timezone.utc)
        delay = (retry5 - now).total_seconds()

        # 10 * 2^5 = 320, but capped at 100
        assert 98 <= delay <= 102

    def test_jitter_backoff_has_randomness(self):
        """Test jitter backoff adds randomness."""
        service = RetryService()

        # Calculate multiple times for same retry count
        retries = [
            service.calculate_next_retry(
                retry_count=2, max_retries=5, retry_policy=RetryPolicy.JITTER, base_delay=10
            )
            for _ in range(10)
        ]

        now = datetime.now(timezone.utc)
        delays = [(r - now).total_seconds() for r in retries]

        # Base = 10 * 2^2 = 40, with jitter (0-50%) = 40-60 range
        assert all(38 <= d <= 62 for d in delays)
        # At least some variation (not all exactly the same)
        assert len(set(int(d) for d in delays)) > 1

    def test_zero_retry_count_returns_immediate(self):
        """Test retry count 0 returns minimal delay."""
        service = RetryService()

        next_retry = service.calculate_next_retry(
            retry_count=0,
            max_retries=3,
            retry_policy=RetryPolicy.EXPONENTIAL,
            base_delay=10,
        )

        now = datetime.now(timezone.utc)
        delay = (next_retry - now).total_seconds()

        # Should be very small delay
        assert delay < 15  # 10 * 2^0 = 10 seconds

    def test_should_retry_within_max_retries(self):
        """Test should_retry returns True when retries available."""
        service = RetryService()

        assert service.should_retry(retry_count=0, max_retries=3) is True
        assert service.should_retry(retry_count=2, max_retries=3) is True

    def test_should_not_retry_when_exhausted(self):
        """Test should_retry returns False when retries exhausted."""
        service = RetryService()

        assert service.should_retry(retry_count=3, max_retries=3) is False
        assert service.should_retry(retry_count=5, max_retries=3) is False

    def test_should_retry_with_zero_max(self):
        """Test should_retry with max_retries=0."""
        service = RetryService()

        assert service.should_retry(retry_count=0, max_retries=0) is False
