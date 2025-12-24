"""Prometheus metrics endpoint."""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session
from schedora.api.deps import get_db
from schedora.observability.metrics import update_worker_metrics, update_queue_metrics
from schedora.services.redis_queue import RedisQueue
from schedora.core.redis import get_redis


router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
def get_metrics(db: Session = Depends(get_db)):
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    # Update gauge metrics before returning
    update_worker_metrics(db)

    # Update queue metrics if Redis is available
    redis = get_redis()
    if redis:
        queue = RedisQueue(redis)
        update_queue_metrics(queue)

    # Generate Prometheus metrics
    return PlainTextResponse(
        content=generate_latest().decode('utf-8'),
        media_type=CONTENT_TYPE_LATEST
    )
