"""Unit tests for core enums."""
import pytest
from schedora.core.enums import JobStatus, RetryPolicy


class TestJobStatusEnum:
    """Test JobStatus enum values and behavior."""

    def test_job_status_has_pending(self):
        """Test JobStatus has PENDING state."""
        assert JobStatus.PENDING.value == "PENDING"

    def test_job_status_has_scheduled(self):
        """Test JobStatus has SCHEDULED state."""
        assert JobStatus.SCHEDULED.value == "SCHEDULED"

    def test_job_status_has_running(self):
        """Test JobStatus has RUNNING state."""
        assert JobStatus.RUNNING.value == "RUNNING"

    def test_job_status_has_success(self):
        """Test JobStatus has SUCCESS state."""
        assert JobStatus.SUCCESS.value == "SUCCESS"

    def test_job_status_has_failed(self):
        """Test JobStatus has FAILED state."""
        assert JobStatus.FAILED.value == "FAILED"

    def test_job_status_has_retrying(self):
        """Test JobStatus has RETRYING state."""
        assert JobStatus.RETRYING.value == "RETRYING"

    def test_job_status_has_dead(self):
        """Test JobStatus has DEAD state."""
        assert JobStatus.DEAD.value == "DEAD"

    def test_job_status_has_canceled(self):
        """Test JobStatus has CANCELED state."""
        assert JobStatus.CANCELED.value == "CANCELED"

    def test_job_status_count(self):
        """Test JobStatus has exactly 8 states."""
        assert len(JobStatus) == 8

    def test_job_status_string_representation(self):
        """Test JobStatus can be used as strings."""
        assert str(JobStatus.PENDING) == "PENDING"
        assert str(JobStatus.SUCCESS) == "SUCCESS"


class TestRetryPolicyEnum:
    """Test RetryPolicy enum values and behavior."""

    def test_retry_policy_has_fixed(self):
        """Test RetryPolicy has FIXED policy."""
        assert RetryPolicy.FIXED.value == "fixed"

    def test_retry_policy_has_exponential(self):
        """Test RetryPolicy has EXPONENTIAL policy."""
        assert RetryPolicy.EXPONENTIAL.value == "exponential"

    def test_retry_policy_has_jitter(self):
        """Test RetryPolicy has JITTER policy."""
        assert RetryPolicy.JITTER.value == "jitter"

    def test_retry_policy_count(self):
        """Test RetryPolicy has exactly 3 policies."""
        assert len(RetryPolicy) == 3

    def test_retry_policy_string_representation(self):
        """Test RetryPolicy can be used as strings."""
        assert str(RetryPolicy.FIXED) == "fixed"
        assert str(RetryPolicy.EXPONENTIAL) == "exponential"
