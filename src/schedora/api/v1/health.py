"""Health check API endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from schedora.api.deps import get_db
from schedora.api.schemas.response import StandardResponse, ResponseCodes

router = APIRouter()


class HealthData(BaseModel):
    """Health check data model."""

    status: str
    database: str


@router.get("/health", response_model=StandardResponse[HealthData])
async def health_check(db: Session = Depends(get_db)) -> StandardResponse[HealthData]:
    """
    Health check endpoint.

    Returns:
        StandardResponse: Service health status including database connection
    """
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    health_data = HealthData(
        status="healthy" if db_status == "connected" else "unhealthy",
        database=db_status,
    )

    return StandardResponse(
        data=health_data,
        code=ResponseCodes.HEALTH_OK,
        httpStatus="OK",
        description="Health check completed successfully"
    )
