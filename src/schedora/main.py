"""FastAPI application factory."""
from fastapi import FastAPI
from schedora.config import get_settings
from schedora.api.v1 import jobs, health, workflows, workers, queue, metrics
from schedora.observability.metrics import init_system_info
from schedora.observability.middleware import MetricsMiddleware

settings = get_settings()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    # Add middleware
    app.add_middleware(MetricsMiddleware)

    # Initialize metrics
    init_system_info(settings.APP_VERSION)

    # Include routers
    app.include_router(jobs.router, prefix=settings.API_V1_PREFIX, tags=["jobs"])
    app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["health"])
    app.include_router(workflows.router, prefix=settings.API_V1_PREFIX, tags=["workflows"])
    app.include_router(workers.router, prefix=settings.API_V1_PREFIX)
    app.include_router(queue.router, prefix=settings.API_V1_PREFIX)
    app.include_router(metrics.router, prefix=settings.API_V1_PREFIX)

    return app


# Create app instance
app = create_app()
