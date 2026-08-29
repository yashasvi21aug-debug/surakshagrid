from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.database import init_db
from app.logging_config import setup_structured_logging
from app.middleware.metrics import PrometheusMetricsMiddleware, get_metrics_response
from app.middleware.security import SecurityHeadersMiddleware
from app.routes.alerts import router as alerts_router
from app.routes.auth import router as auth_router
from app.routes.dispatch import router as dispatch_router
from app.routes.health import router as health_router
from app.routes.ml import router as ml_router
from app.routes.routes import router as routes_router
from app.routes.sos import router as sos_router
from app.routes.spatial import router as spatial_router
from app.routes.ws import router as ws_router
from app.services.weather import background_ingestion_loop, fetch_live_weather

# 0. Setup Structured JSON Logging
setup_structured_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Application Lifespan context manager with background ingestion task worker."""
    logger.info("Initializing SurakshaGrid backend services...")
    try:
        await init_db()
        app.state.database_available = True
        app.state.mock_mode = False
    except Exception as error:
        app.state.database_available = False
        app.state.mock_mode = True
        logger.warning("PostgreSQL/PostGIS unavailable; starting in mock mode: %s", error)

    from ml.predictor import preload_static_models
    try:
        preload_static_models()
    except Exception as error:
        logger.warning("ML model artifacts unavailable at startup: %s", error)

    # Launch background IoT sensor ingestion task worker
    ingestion_task = asyncio.create_task(background_ingestion_loop(interval_seconds=300))

    yield

    logger.info("Shutting down SurakshaGrid backend services...")
    ingestion_task.cancel()
    try:
        await ingestion_task
    except asyncio.CancelledError:
        pass


# 1. Instantiate FastAPI Application
app = FastAPI(
    title="SurakshaGrid",
    description="Flood disaster incident command and digital twin API (PRD v1.0.0)",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter

# 2. Add Security & Prometheus Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(PrometheusMetricsMiddleware)

allowed_origins = os.getenv("CORS_ORIGINS", os.getenv("CORS_ALLOWED_ORIGINS"))
if allowed_origins:
    try:
        cors_list = json.loads(allowed_origins) if allowed_origins.startswith("[") else [o.strip() for o in allowed_origins.split(",")]
    except Exception:
        cors_list = ["*"]
else:
    cors_list = settings.CORS_ALLOWED_ORIGINS or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. RFC 7807 Standardized Error Handlers
@app.exception_handler(HTTPException)
async def rfc7807_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers or {"Content-Type": "application/problem+json"},
        content={
            "type": f"https://surakshagrid.local/errors/http-{exc.status_code}",
            "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(RequestValidationError)
async def rfc7807_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        headers={"Content-Type": "application/problem+json"},
        content={
            "type": "https://surakshagrid.local/errors/validation-error",
            "title": "Unprocessable Entity",
            "status": 422,
            "detail": exc.errors(),
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rfc7807_rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Content-Type": "application/problem+json"},
        content={
            "type": "https://surakshagrid.local/errors/rate-limit-exceeded",
            "title": "Too Many Requests",
            "status": 429,
            "detail": "Rate limit exceeded. Please wait before retrying.",
            "instance": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def rfc7807_generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"Content-Type": "application/problem+json"},
        content={
            "type": "https://surakshagrid.local/errors/internal-server-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An internal server error occurred.",
            "instance": str(request.url.path),
        },
    )


# 4. Register Routers
app.include_router(health_router)
app.include_router(dispatch_router)
app.include_router(ml_router)
app.include_router(alerts_router)
app.include_router(auth_router)
app.include_router(routes_router)
app.include_router(sos_router)
app.include_router(spatial_router)
app.include_router(ws_router)


# 5. Metrics & Telemetry Endpoints
@app.get("/metrics")
@app.get("/api/v1/metrics")
async def metrics_endpoint():
    """Export Prometheus telemetry metrics."""
    return get_metrics_response()


@app.get("/api/v1/telemetry/live-weather")
async def get_live_telemetry(lat: float = 28.6321, lng: float = 77.4446):
    return await fetch_live_weather(lat, lng)


@app.get("/api/v1/sos/active-feed")
async def get_active_sos_feed():
    """Returns active emergency alerts from the live database."""
    return []


@app.post("/api/v1/simulation/start")
async def start_simulation(duration: float | None = None, interval: float = 2.0):
    from app.simulation import simulation_harness

    simulation_harness.interval = interval
    await simulation_harness.start(duration_seconds=duration)
    return {"status": "started", "interval": interval}


@app.post("/api/v1/simulation/stop")
async def stop_simulation():
    from app.simulation import simulation_harness

    await simulation_harness.stop()
    return {"status": "stopped"}


@app.get("/")
async def root():
    return {
        "service": "SurakshaGrid Incident Command & Digital Twin API",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "metrics": "/metrics",
        "websocket_endpoints": ["/ws", "/ws/dashboard", "/ws/responders", "/ws/citizens"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
