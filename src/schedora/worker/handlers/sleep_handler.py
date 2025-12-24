"""Sleep handler - sleeps for specified duration then succeeds."""
import asyncio
from typing import Dict, Any


async def sleep_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sleep handler that sleeps for a duration then succeeds.

    Useful for testing async job execution and timeouts.

    Args:
        payload: Job payload with optional 'duration' key (default: 1 second)

    Returns:
        Dict[str, Any]: Result with status and duration
    """
    duration = payload.get("duration", 1)
    await asyncio.sleep(duration)

    return {
        "status": "completed",
        "duration": duration,
    }
