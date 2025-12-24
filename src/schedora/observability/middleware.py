"""Middleware for request/response metrics."""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge


# HTTP metrics
http_requests_total = Counter(
    'schedora_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'schedora_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

http_requests_in_progress = Gauge(
    'schedora_http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics."""

    async def dispatch(self, request: Request, call_next):
        """
        Process request and track metrics.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/api/v1/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Track request start
        start_time = time.time()
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        try:
            # Process request
            response = await call_next(request)

            # Track metrics
            duration = time.time() - start_time
            status = response.status_code

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            return response

        except Exception as e:
            # Track error metrics
            duration = time.time() - start_time

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            raise e

        finally:
            # Always decrement in-progress count
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
