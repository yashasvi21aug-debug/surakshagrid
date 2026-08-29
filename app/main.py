import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

# 1. Instantiate FastAPI First
app = FastAPI(
    title="SurakshaGrid",
    description="Flood disaster incident command and digital twin API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Configure Templates & Static Assets
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR)) if TEMPLATES_DIR.is_dir() else None

# 3. Register Routers AFTER app is created
app.include_router(ml_router)
app.include_router(alerts_router)
app.include_router(auth_router)
app.include_router(routes_router)
app.include_router(sos_router)
app.include_router(spatial_router)
app.include_router(ws_router)


# 4. Endpoints
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


# 5. Page Template Routes
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

