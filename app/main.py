from fastapi import FastAPI

from app.database import init_db
from app.routes.ml import router as ml_router
from app.routes.routes import router as routes_router
from app.routes.sos import router as sos_router
from app.routes.spatial import router as spatial_router
from app.routes.ws import router as ws_router

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
    await init_db()


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "SurakshaGrid"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to SurakshaGrid API"}
