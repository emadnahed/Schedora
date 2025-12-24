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


class WorkflowStatus(str, Enum):
    """
    Workflow execution status states.

    - PENDING: No jobs have started executing
    - RUNNING: At least one job is running or scheduled
    - COMPLETED: All jobs completed successfully
    - FAILED: At least one job failed
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    def __str__(self) -> str:
        """Return string representation of the enum value."""
        return self.value


class WorkerStatus(str, Enum):
    """
    Worker lifecycle status states.

    State flow:
        STARTING → ACTIVE → STOPPING → STOPPED
                      ↓
                   STALE (detected by heartbeat timeout)

    - STARTING: Worker is initializing
    - ACTIVE: Worker is running and processing jobs
    - STALE: Worker missed heartbeat (requires intervention)
    - STOPPING: Worker is shutting down gracefully
    - STOPPED: Worker has shut down
    """

    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"

    def __str__(self) -> str:
        """Return string representation of the enum value."""
        return self.value
