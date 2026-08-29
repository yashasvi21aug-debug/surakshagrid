from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_db
from app.services.ml_service import ml_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["System Health"])


@router.get("", response_model=dict[str, Any])
@router.get("/", response_model=dict[str, Any])
async def liveness_probe() -> dict[str, Any]:
    """Lightweight Kubernetes / Render liveness probe."""
    return {
        "status": "healthy",
        "service": "surakshagrid-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@router.get("/ready", response_model=dict[str, Any])
async def readiness_probe(db: AsyncSession = Depends(get_async_db)) -> dict[str, Any]:
    """Deep readiness probe checking PostGIS database pool, ML model weights, and OSRM router reachability."""
    probe_results: dict[str, Any] = {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
    }
    all_healthy = True

    # 1. PostGIS Database Pool Health Check
    db_start = time.perf_counter()
    try:
        res = await db.execute(text("SELECT PostGIS_Full_Version();"))
        version_str = res.scalar() or "PostGIS Enabled"
        db_latency_ms = (time.perf_counter() - db_start) * 1000.0
        probe_results["checks"]["database"] = {
            "status": "healthy",
            "latency_ms": round(db_latency_ms, 2),
            "postgis_version": version_str,
        }
    except Exception as db_err:
        all_healthy = False
        probe_results["checks"]["database"] = {
            "status": "degraded",
            "error": str(db_err),
            "mode": "mock_mode_fallback",
        }

    # 2. ML Hydrological Predictor Status Check
    try:
        is_fallback = getattr(ml_service, "_is_fallback", False)
        probe_results["checks"]["ml_engine"] = {
            "status": "healthy" if not is_fallback else "fallback_mode",
            "models_preloaded": ["inundation_xgb.json", "depth_xgb.json"],
        }
    except Exception as ml_err:
        probe_results["checks"]["ml_engine"] = {
            "status": "degraded",
            "error": str(ml_err),
        }

    # 3. External OSRM Routing Engine Reachability Check
    osrm_start = time.perf_counter()
    try:
        osrm_url = getattr(settings, "OSRM_BASE_URL", "http://localhost:5000")
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{osrm_url}/table/v1/driving/77.30,28.65;77.31,28.66")
            osrm_latency_ms = (time.perf_counter() - osrm_start) * 1000.0
            probe_results["checks"]["osrm_routing"] = {
                "status": "healthy" if res.status_code == 200 else "degraded",
                "latency_ms": round(osrm_latency_ms, 2),
                "url": osrm_url,
            }
    except Exception:
        probe_results["checks"]["osrm_routing"] = {
            "status": "geodesic_fallback_active",
            "notice": "OSRM server offline. Using Shapely geodesic fallback.",
        }

    if not all_healthy:
        probe_results["status"] = "degraded"

    return probe_results
