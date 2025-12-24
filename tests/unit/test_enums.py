"""Unit tests for core enums."""
import pytest
from schedora.core.enums import JobStatus, RetryPolicy, WorkerStatus


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


class TestWorkerStatusEnum:
    """Test WorkerStatus enum values and behavior."""

    def test_worker_status_has_starting(self):
        """Test WorkerStatus has STARTING state."""
        assert WorkerStatus.STARTING.value == "STARTING"

    def test_worker_status_has_active(self):
        """Test WorkerStatus has ACTIVE state."""
        assert WorkerStatus.ACTIVE.value == "ACTIVE"

    def test_worker_status_has_stale(self):
        """Test WorkerStatus has STALE state."""
        assert WorkerStatus.STALE.value == "STALE"

    def test_worker_status_has_stopping(self):
        """Test WorkerStatus has STOPPING state."""
        assert WorkerStatus.STOPPING.value == "STOPPING"

    def test_worker_status_has_stopped(self):
        """Test WorkerStatus has STOPPED state."""
        assert WorkerStatus.STOPPED.value == "STOPPED"

    def test_worker_status_count(self):
        """Test WorkerStatus has exactly 5 states."""
        assert len(WorkerStatus) == 5

    def test_worker_status_string_representation(self):
        """Test WorkerStatus can be used as strings."""
        assert str(WorkerStatus.ACTIVE) == "ACTIVE"
        assert str(WorkerStatus.STOPPED) == "STOPPED"
