"""Echo handler - returns payload unchanged."""
from typing import Dict, Any


async def echo_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Echo handler that returns the payload unchanged.

    Useful for testing job execution without side effects.

    Args:
        payload: Job payload

    Returns:
        Dict[str, Any]: Same payload unchanged
    """
    return payload
