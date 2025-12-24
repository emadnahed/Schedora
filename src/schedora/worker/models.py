"""Worker data models and result classes."""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ExecutionResult:
    """
    Result of job execution.

    Tracks whether execution succeeded and any result/error data.
    """

    success: bool
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
