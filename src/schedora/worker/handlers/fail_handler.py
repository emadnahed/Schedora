"""Fail handler - always raises an exception."""
from typing import Dict, Any


async def fail_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fail handler that always raises an exception.

    Useful for testing error handling and retry logic.

    Args:
        payload: Job payload with optional 'error_message' and 'error_type'

    Raises:
        Exception: Always raises to simulate job failure

    Returns:
        Dict[str, Any]: Never returns
    """
    error_message = payload.get("error_message", "Simulated job failure")
    error_type = payload.get("error_type", "Exception")

    # Map error type string to actual exception class
    error_classes = {
        "Exception": Exception,
        "ValueError": ValueError,
        "RuntimeError": RuntimeError,
        "KeyError": KeyError,
    }

    error_class = error_classes.get(error_type, Exception)
    raise error_class(error_message)
