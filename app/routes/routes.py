from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.routing_service import RoutingService

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])
routing_service = RoutingService()


@router.post("/safe-dispatch")
async def safe_dispatch_route(
    payload: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    origin_coords = payload.get("origin_coords")
    destination_coords = payload.get("destination_coords")
    profile = payload.get("profile", "driving")

    if not origin_coords or not destination_coords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="origin_coords and destination_coords are required",
        )

    try:
        origin = (float(origin_coords[1]), float(origin_coords[0]))
        destination = (float(destination_coords[1]), float(destination_coords[0]))
    except (TypeError, ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coordinates must be [lng, lat] pairs",
        ) from None

    return await routing_service.get_safe_dispatch_route(
        db=db,
        origin_coords=origin,
        destination_coords=destination,
        profile=profile,
    )
