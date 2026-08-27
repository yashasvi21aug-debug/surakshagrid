import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.database import init_db
from app.routes.ml import router as ml_router
from app.routes.routes import router as routes_router
from app.routes.sos import router as sos_router
from app.routes.spatial import router as spatial_router
from app.routes.ws import router as ws_router

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="SurakshaGrid",
    description="Flood disaster incident command and digital twin API",
    version="1.0.0",
)

app.include_router(ml_router)
app.include_router(routes_router)
app.include_router(sos_router)
app.include_router(spatial_router)
app.include_router(ws_router)


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


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to SurakshaGrid API"}


@app.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "index.html")
