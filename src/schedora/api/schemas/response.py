"""Standard API response schemas."""
from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')


class StandardResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    data: T = Field(..., description="Response data")
    code: str = Field(..., description="Response code")
    httpStatus: str = Field(..., description="HTTP status text")
    description: str = Field(..., description="Response description")

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    """Standard error response."""

    data: Optional[Any] = Field(None, description="Error details")
    code: str = Field(..., description="Error code")
    httpStatus: str = Field(..., description="HTTP status text")
    description: str = Field(..., description="Error description")

    model_config = {"from_attributes": True}


# Response codes
class ResponseCodes:
    """Standard response codes."""

    # Success codes (2xx)
    JOB_CREATED = "JOB_0001"
    JOB_RETRIEVED = "JOB_0002"
    JOB_CANCELED = "JOB_0003"

    WORKFLOW_CREATED = "WF_0001"
    WORKFLOW_RETRIEVED = "WF_0002"
    WORKFLOW_STATUS_RETRIEVED = "WF_0003"
    JOB_ADDED_TO_WORKFLOW = "WF_0004"

    HEALTH_OK = "HEALTH_0001"

    # Error codes (4xx, 5xx)
    JOB_NOT_FOUND = "JOB_4001"
    JOB_DUPLICATE_KEY = "JOB_4002"
    JOB_INVALID_TRANSITION = "JOB_4003"

    WORKFLOW_NOT_FOUND = "WF_4001"
    WORKFLOW_DUPLICATE_NAME = "WF_4002"

    VALIDATION_ERROR = "ERR_4001"
    INTERNAL_ERROR = "ERR_5001"
