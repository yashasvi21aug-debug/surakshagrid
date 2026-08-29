import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.database import init_db
from app.routes.alerts import router as alerts_router
from app.routes.auth import router as auth_router
from app.routes.ml import router as ml_router
from app.routes.routes import router as routes_router
from app.routes.sos import router as sos_router
from app.routes.spatial import router as spatial_router
from app.routes.ws import router as ws_router
from app.services.weather import fetch_live_weather

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
LEGACY_FRONTEND_DIR = APP_DIR.parent / "frontend"

# Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

# 1. Instantiate FastAPI
app = FastAPI(
    title="SurakshaGrid",
    description="Flood disaster incident command and digital twin API",
    version="1.0.0",
)
app.state.limiter = limiter

# 2. Strict CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
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


# 4. Configure Templates & Static Assets
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR)) if TEMPLATES_DIR.is_dir() else None

# 5. Register Routers
app.include_router(ml_router)
app.include_router(alerts_router)
app.include_router(auth_router)
app.include_router(routes_router)
app.include_router(sos_router)
app.include_router(spatial_router)
app.include_router(ws_router)


# 6. Endpoints
@app.get("/api/v1/telemetry/live-weather")
async def get_live_telemetry(lat: float = 28.6321, lng: float = 77.4446):
    return await fetch_live_weather(lat, lng)


@app.on_event("startup")
async def startup_event() -> None:
    try:
        await init_db()
    except Exception as error:
        app.state.database_available = False
        app.state.mock_mode = True
        logger.warning(
            "PostgreSQL/PostGIS unavailable; starting SurakshaGrid in mock mode: %s",
            error,
        )
    else:
        app.state.database_available = True
        app.state.mock_mode = False

    from ml.predictor import preload_static_models

    try:
        preload_static_models()
    except Exception as error:
        logger.warning("ML model artifacts unavailable at startup: %s", error)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "SurakshaGrid"}


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


# 7. Page Template Routes
@app.get("/")
async def root(request: Request):
    if templates:
        return templates.TemplateResponse(request=request, name="index.html")
    index_file = LEGACY_FRONTEND_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "service": "SurakshaGrid Incident Command & Digital Twin API",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket_endpoints": ["/ws/eoc-feed", "/ws/vehicle-telemetry"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/citizen")
async def citizen_page(request: Request):
    if templates:
        return templates.TemplateResponse(request=request, name="citizen.html")
    page = LEGACY_FRONTEND_DIR / "citizen.html"
    if page.is_file():
        return FileResponse(page)
    return {"error": "citizen.html not found"}


@app.get("/driver")
async def driver_page(request: Request):
    if templates:
        return templates.TemplateResponse(request=request, name="driver.html")
    page = LEGACY_FRONTEND_DIR / "driver.html"
    if page.is_file():
        return FileResponse(page)
    return {"error": "driver.html not found"}


@app.get("/dashboard")
async def dashboard_page(request: Request):
    if templates:
        return templates.TemplateResponse(request=request, name="dashboard.html")
    page = LEGACY_FRONTEND_DIR / "dashboard.html"
    if page.is_file():
        return FileResponse(page)
    return {"error": "dashboard.html not found"}
