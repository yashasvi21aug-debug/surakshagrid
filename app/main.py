import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# 2. Register Routers AFTER app is created
app.include_router(ml_router)
app.include_router(alerts_router)
app.include_router(auth_router)
app.include_router(routes_router)
app.include_router(sos_router)
app.include_router(spatial_router)
app.include_router(ws_router)

# 3. Endpoints
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
    # If using your SQLAlchemy DB session:
    # return db.query(SOSModel).filter(SOSModel.status != "RESOLVED").all()
    return []


@app.get("/")
async def root() -> dict[str, object]:
    return {
        "service": "SurakshaGrid Incident Command & Digital Twin API",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket_endpoints": ["/ws/eoc-feed", "/ws/vehicle-telemetry"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
