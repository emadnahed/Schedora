"""Core enumerations for the Schedora job orchestration platform."""
from enum import Enum


class JobStatus(str, Enum):
    """
    Job state machine states.

    State flow:
        PENDING → SCHEDULED → RUNNING → SUCCESS/FAILED
                                   ↓         ↓
                               RETRYING   DEAD
             CANCELED (from any non-terminal state)
    """

    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD = "DEAD"
    CANCELED = "CANCELED"

    def __str__(self) -> str:
        """Return string representation of the enum value."""
        return self.value


class RetryPolicy(str, Enum):
    """
    Retry backoff policies for failed jobs.

    - FIXED: Retry with fixed delay
    - EXPONENTIAL: Retry with exponentially increasing delay
    - JITTER: Retry with exponential delay plus random jitter
    """

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    JITTER = "jitter"

    def __str__(self) -> str:
        """Return string representation of the enum value."""
        return self.value
