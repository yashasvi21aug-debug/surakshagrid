from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

# 1. Prometheus Metrics Definitions
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

SOS_INGEST_TOTAL = Counter(
    "sos_ingest_total",
    "Total citizen emergency SOS submissions ingested",
    ["category", "status"],
)

ACTIVE_WEBSOCKET_CONNECTIONS = Gauge(
    "active_websocket_connections",
    "Number of active WebSocket connections across rooms",
    ["room"],
)

SPATIAL_QUERY_DURATION_SECONDS = Histogram(
    "spatial_query_duration_seconds",
    "PostGIS spatial query and polygon intersection duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for structured JSON logging with Correlation IDs and Prometheus HTTP metrics collection."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Correlation ID Handling
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        # Inject X-Request-ID response header
        response.headers["X-Request-ID"] = request_id

        # Record HTTP metrics
        path = request.url.path
        if not path.endswith("/metrics") and not path.endswith("/health"):
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                path=path,
                status_code=response.status_code,
            ).observe(process_time)

        return response


def get_metrics_response() -> Response:
    """Return raw Prometheus metrics string."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
