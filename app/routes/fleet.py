from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.services.volunteer_fleet import volunteer_fleet_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fleet", tags=["fleet"])


@router.get("/available", response_model=dict[str, Any])
async def get_available_fleet_assets(
    water_depth_m: float = Query(default=0.5, ge=0.0, le=10.0),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Fetch real-time available rescue assets near an incident cluster as GeoJSON (PRD Section 3 & 4.4)."""
    return await volunteer_fleet_service.get_available_fleet_geojson(water_depth_m, db)


@router.post("/dispatch", response_model=dict[str, Any])
async def dispatch_fleet_asset(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Deploy selected fleet assets to active incident coordinates with calculated waypoints."""
    asset_id = payload.get("asset_id", "ASSET-NDRF-BOAT-01")
    target_lat = float(payload.get("lat", 28.5355))
    target_lng = float(payload.get("lng", 77.3910))

    return await volunteer_fleet_service.dispatch_asset_to_incident(
        asset_id, target_lat, target_lng, db
    )
