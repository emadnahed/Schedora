"""FastAPI application factory."""
from fastapi import FastAPI
from schedora.config import get_settings
from schedora.api.v1 import jobs, health, workflows, workers

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

    # Include routers
    app.include_router(jobs.router, prefix=settings.API_V1_PREFIX, tags=["jobs"])
    app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["health"])
    app.include_router(workflows.router, prefix=settings.API_V1_PREFIX, tags=["workflows"])
    app.include_router(workers.router, prefix=settings.API_V1_PREFIX)

    return app


# Create app instance
app = create_app()
