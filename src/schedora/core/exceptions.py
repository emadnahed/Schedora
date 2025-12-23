"""Custom exceptions for Schedora."""


class SchedoraException(Exception):
    """Base exception for all Schedora-specific exceptions."""

    pass


class InvalidStateTransitionError(SchedoraException):
    """Raised when attempting an invalid job state transition."""

    pass


class JobNotFoundError(SchedoraException):
    """Raised when a job is not found in the database."""

    pass


class DuplicateIdempotencyKeyError(SchedoraException):
    """Raised when attempting to create a job with a duplicate idempotency key."""

    pass
