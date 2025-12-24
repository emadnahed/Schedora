"""Handler registry for job type to function mapping."""
from typing import Dict, Callable, List, Any


class HandlerRegistry:
    """
    Registry for mapping job types to handler functions.

    Provides a simple dictionary-based registry for registering
    and retrieving handler functions by job type.
    """

    def __init__(self):
        """Initialize empty handler registry."""
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, job_type: str, handler: Callable) -> None:
        """
        Register a handler function for a job type.

        Args:
            job_type: The job type identifier
            handler: The handler function (can be sync or async)

        Raises:
            ValueError: If handler for this job type already registered
        """
        if job_type in self._handlers:
            raise ValueError(f"Handler for job type '{job_type}' already registered")

        self._handlers[job_type] = handler

    def register(self, job_type: str) -> Callable:
        """
        Decorator for registering a handler function.

        Args:
            job_type: The job type identifier

        Returns:
            Callable: Decorator function

        Example:
            >>> registry = HandlerRegistry()
            >>> @registry.register("echo")
            >>> async def echo_handler(payload):
            >>>     return payload
        """

        def decorator(handler: Callable) -> Callable:
            self.register_handler(job_type, handler)
            return handler

        return decorator

    def get_handler(self, job_type: str) -> Callable:
        """
        Get the handler function for a job type.

        Args:
            job_type: The job type identifier

        Returns:
            Callable: The registered handler function

        Raises:
            KeyError: If no handler registered for this job type
        """
        if job_type not in self._handlers:
            raise KeyError(f"No handler registered for job type: {job_type}")

        return self._handlers[job_type]

    def has_handler(self, job_type: str) -> bool:
        """
        Check if a handler is registered for a job type.

        Args:
            job_type: The job type identifier

        Returns:
            bool: True if handler registered, False otherwise
        """
        return job_type in self._handlers

    def list_handlers(self) -> List[str]:
        """
        List all registered job types.

        Returns:
            List[str]: List of registered job types
        """
        return list(self._handlers.keys())
