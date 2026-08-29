from __future__ import annotations

import logging
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def sanitize_gps_telemetry(lat: float, lng: float, accuracy: float | None = 10.0) -> tuple[float, float, float]:
    """Validate and sanitize incoming GPS coordinates and accuracy telemetry."""
    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Latitude {lat} out of valid geospatial range [-90.0, +90.0]",
        )
    if not (-180.0 <= lng <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Longitude {lng} out of valid geospatial range [-180.0, +180.0]",
        )

    # Clamp accuracy margin between 1.0m and 500.0m to prevent telemetry poisoning
    raw_acc = accuracy if accuracy is not None else 10.0
    clamped_acc = max(1.0, min(float(raw_acc), 500.0))

    return float(lat), float(lng), clamped_acc


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """OWASP Recommended Security Response Headers Middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Apply OWASP Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com; "
            "img-src 'self' data: blob: https://*.basemaps.cartocdn.com; "
            "connect-src 'self' wss: ws: https:;"
        )

        return response
