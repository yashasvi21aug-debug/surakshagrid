from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.services.shelter_allocation import shelter_allocation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/shelters", tags=["shelters"])


@router.get("", response_model=dict[str, Any])
async def get_evacuation_shelters(
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Return all operational evacuation centers with real-time capacity meters as GeoJSON (PRD Section 4.4)."""
    return await shelter_allocation_service.get_all_shelters_geojson(db)


@router.post("/allocate", response_model=dict[str, Any])
async def allocate_shelter_destination(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Assign a cluster of rescued citizens to optimal destination shelter and decrement available capacity."""
    lat = float(payload.get("lat", 28.5355))
    lng = float(payload.get("lng", 77.3910))
    headcount = int(payload.get("headcount", 4))
    requires_med = bool(payload.get("requires_medical", False))

    return await shelter_allocation_service.allocate_rescued_cluster(
        lat, lng, headcount, requires_med, db
    )
