"""Unit tests for JobStateMachine - pure logic, no DB."""
import pytest
from schedora.core.enums import JobStatus
from schedora.services.state_machine import JobStateMachine
from schedora.core.exceptions import InvalidStateTransitionError


class TestJobStateMachine:
    """Test job state machine transitions and validation."""

    def test_valid_transition_pending_to_scheduled(self):
        """Test valid transition: PENDING -> SCHEDULED."""
        assert JobStateMachine.can_transition(
            JobStatus.PENDING, JobStatus.SCHEDULED
        ) is True

    def test_valid_transition_scheduled_to_running(self):
        """Test valid transition: SCHEDULED -> RUNNING."""
        assert JobStateMachine.can_transition(
            JobStatus.SCHEDULED, JobStatus.RUNNING
        ) is True

    def test_valid_transition_running_to_success(self):
        """Test valid transition: RUNNING -> SUCCESS."""
        assert JobStateMachine.can_transition(
            JobStatus.RUNNING, JobStatus.SUCCESS
        ) is True

    def test_valid_transition_running_to_failed(self):
        """Test valid transition: RUNNING -> FAILED."""
        assert JobStateMachine.can_transition(
            JobStatus.RUNNING, JobStatus.FAILED
        ) is True

    def test_valid_transition_running_to_retrying(self):
        """Test valid transition: RUNNING -> RETRYING."""
        assert JobStateMachine.can_transition(
            JobStatus.RUNNING, JobStatus.RETRYING
        ) is True

    def test_valid_transition_failed_to_retrying(self):
        """Test valid transition: FAILED -> RETRYING."""
        assert JobStateMachine.can_transition(
            JobStatus.FAILED, JobStatus.RETRYING
        ) is True

    def test_valid_transition_failed_to_dead(self):
        """Test valid transition: FAILED -> DEAD."""
        assert JobStateMachine.can_transition(
            JobStatus.FAILED, JobStatus.DEAD
        ) is True

    def test_valid_transition_retrying_to_scheduled(self):
        """Test valid transition: RETRYING -> SCHEDULED."""
        assert JobStateMachine.can_transition(
            JobStatus.RETRYING, JobStatus.SCHEDULED
        ) is True

    def test_valid_transition_pending_to_running(self):
        """Test valid transition: PENDING -> RUNNING (workers can claim and execute)."""
        assert JobStateMachine.can_transition(
            JobStatus.PENDING, JobStatus.RUNNING
        ) is True

    def test_invalid_transition_pending_to_success(self):
        """Test invalid transition: PENDING -> SUCCESS."""
        assert JobStateMachine.can_transition(
            JobStatus.PENDING, JobStatus.SUCCESS
        ) is False

    def test_invalid_transition_from_success(self):
        """Test that SUCCESS is terminal and cannot transition."""
        assert JobStateMachine.can_transition(
            JobStatus.SUCCESS, JobStatus.RUNNING
        ) is False
        assert JobStateMachine.can_transition(
            JobStatus.SUCCESS, JobStatus.PENDING
        ) is False

    def test_invalid_transition_from_dead(self):
        """Test that DEAD is terminal and cannot transition."""
        assert JobStateMachine.can_transition(
            JobStatus.DEAD, JobStatus.RUNNING
        ) is False
        assert JobStateMachine.can_transition(
            JobStatus.DEAD, JobStatus.RETRYING
        ) is False

    def test_invalid_transition_from_canceled(self):
        """Test that CANCELED is terminal and cannot transition."""
        assert JobStateMachine.can_transition(
            JobStatus.CANCELED, JobStatus.RUNNING
        ) is False
        assert JobStateMachine.can_transition(
            JobStatus.CANCELED, JobStatus.PENDING
        ) is False

    def test_validate_transition_success(self):
        """Test validate_transition does not raise on valid transition."""
        # Should not raise
        JobStateMachine.validate_transition(
            JobStatus.PENDING, JobStatus.SCHEDULED
        )

    def test_validate_transition_raises_on_invalid(self):
        """Test validate_transition raises exception on invalid transition."""
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            JobStateMachine.validate_transition(
                JobStatus.SUCCESS, JobStatus.RUNNING
            )
        assert "Invalid state transition" in str(exc_info.value)
        assert "SUCCESS" in str(exc_info.value)
        assert "RUNNING" in str(exc_info.value)

    def test_is_terminal_success(self):
        """Test that SUCCESS is identified as terminal state."""
        assert JobStateMachine.is_terminal(JobStatus.SUCCESS) is True

    def test_is_terminal_dead(self):
        """Test that DEAD is identified as terminal state."""
        assert JobStateMachine.is_terminal(JobStatus.DEAD) is True

    def test_is_terminal_canceled(self):
        """Test that CANCELED is identified as terminal state."""
        assert JobStateMachine.is_terminal(JobStatus.CANCELED) is True

    def test_is_terminal_pending(self):
        """Test that PENDING is not terminal state."""
        assert JobStateMachine.is_terminal(JobStatus.PENDING) is False

    def test_is_terminal_running(self):
        """Test that RUNNING is not terminal state."""
        assert JobStateMachine.is_terminal(JobStatus.RUNNING) is False

    def test_get_valid_transitions_from_pending(self):
        """Test getting all valid next states from PENDING."""
        valid_states = JobStateMachine.get_valid_transitions(JobStatus.PENDING)
        assert valid_states == {JobStatus.SCHEDULED, JobStatus.RUNNING, JobStatus.CANCELED}

    def test_get_valid_transitions_from_running(self):
        """Test getting all valid next states from RUNNING."""
        valid_states = JobStateMachine.get_valid_transitions(JobStatus.RUNNING)
        assert valid_states == {
            JobStatus.SUCCESS,
            JobStatus.FAILED,
            JobStatus.RETRYING,
            JobStatus.CANCELED,
        }

    def test_get_valid_transitions_from_terminal_state(self):
        """Test terminal states have no valid transitions."""
        assert JobStateMachine.get_valid_transitions(JobStatus.SUCCESS) == set()
        assert JobStateMachine.get_valid_transitions(JobStatus.DEAD) == set()
        assert JobStateMachine.get_valid_transitions(JobStatus.CANCELED) == set()

    def test_cancel_from_pending(self):
        """Test cancellation is possible from PENDING."""
        assert JobStateMachine.can_transition(
            JobStatus.PENDING, JobStatus.CANCELED
        ) is True

    def test_cancel_from_scheduled(self):
        """Test cancellation is possible from SCHEDULED."""
        assert JobStateMachine.can_transition(
            JobStatus.SCHEDULED, JobStatus.CANCELED
        ) is True

    def test_cancel_from_running(self):
        """Test cancellation is possible from RUNNING."""
        assert JobStateMachine.can_transition(
            JobStatus.RUNNING, JobStatus.CANCELED
        ) is True

    def test_retry_flow_complete(self):
        """Test complete retry flow: RUNNING -> FAILED -> RETRYING -> SCHEDULED."""
        assert JobStateMachine.can_transition(JobStatus.RUNNING, JobStatus.FAILED)
        assert JobStateMachine.can_transition(JobStatus.FAILED, JobStatus.RETRYING)
        assert JobStateMachine.can_transition(JobStatus.RETRYING, JobStatus.SCHEDULED)

    def test_dead_state_reached_after_max_retries(self):
        """Test that DEAD state is reachable from FAILED."""
        assert JobStateMachine.can_transition(JobStatus.FAILED, JobStatus.DEAD)
