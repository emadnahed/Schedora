"""Health check API endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from schedora.api.deps import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Service health status including database connection
    """
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        database=db_status,
    )
