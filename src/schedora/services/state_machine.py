"""Job state machine logic for managing valid job state transitions."""
from typing import Set, Dict
from schedora.core.enums import JobStatus
from schedora.core.exceptions import InvalidStateTransitionError


class JobStateMachine:
    """
    Defines valid state transitions for jobs.
    Ensures atomic and valid state changes.

    State Diagram:
        PENDING → SCHEDULED → RUNNING → SUCCESS/FAILED
                                   ↓         ↓
                               RETRYING   DEAD
             CANCELED (from any non-terminal)
    """

    # Define valid transitions as a mapping from current state to allowed next states
    TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
        JobStatus.PENDING: {JobStatus.SCHEDULED, JobStatus.CANCELED},
        JobStatus.SCHEDULED: {JobStatus.RUNNING, JobStatus.CANCELED},
        JobStatus.RUNNING: {
            JobStatus.SUCCESS,
            JobStatus.FAILED,
            JobStatus.RETRYING,
            JobStatus.CANCELED,
        },
        JobStatus.FAILED: {JobStatus.RETRYING, JobStatus.DEAD},
        JobStatus.RETRYING: {JobStatus.SCHEDULED},
        JobStatus.SUCCESS: set(),  # Terminal state
        JobStatus.DEAD: set(),  # Terminal state
        JobStatus.CANCELED: set(),  # Terminal state
    }

    TERMINAL_STATES = {JobStatus.SUCCESS, JobStatus.DEAD, JobStatus.CANCELED}

    @classmethod
    def can_transition(cls, from_state: JobStatus, to_state: JobStatus) -> bool:
        """
        Check if transition from from_state to to_state is valid.

        Args:
            from_state: Current job status
            to_state: Desired job status

        Returns:
            bool: True if transition is valid, False otherwise
        """
        return to_state in cls.TRANSITIONS.get(from_state, set())

    @classmethod
    def validate_transition(cls, from_state: JobStatus, to_state: JobStatus) -> None:
        """
        Validate state transition and raise exception if invalid.

        Args:
            from_state: Current job status
            to_state: Desired job status

        Raises:
            InvalidStateTransitionError: If transition is not valid
        """
        if not cls.can_transition(from_state, to_state):
            raise InvalidStateTransitionError(
                f"Invalid state transition: {from_state} -> {to_state}"
            )

    @classmethod
    def is_terminal(cls, state: JobStatus) -> bool:
        """
        Check if state is terminal (no further transitions possible).

        Args:
            state: Job status to check

        Returns:
            bool: True if terminal state, False otherwise
        """
        return state in cls.TERMINAL_STATES

    @classmethod
    def get_valid_transitions(cls, from_state: JobStatus) -> Set[JobStatus]:
        """
        Get all valid next states from current state.

        Args:
            from_state: Current job status

        Returns:
            Set[JobStatus]: Set of valid next states
        """
        return cls.TRANSITIONS.get(from_state, set())
