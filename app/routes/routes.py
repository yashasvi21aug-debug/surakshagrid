from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import OfficerPrincipal, require_role
from app.services.routing import FloodAvoidanceRoutingService, RoutingError, RoutingService

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])
routing_service = RoutingService()
evacuation_routing_service = routing_service


def _coordinate(value: object, field_name: str) -> tuple[float, float]:
    if isinstance(value, dict):
        try:
            return float(value["lng"]), float(value["lat"])
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=f"{field_name} must contain lat and lng") from error
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=f"{field_name} must be [lng, lat]") from error
    raise HTTPException(status_code=400, detail=f"{field_name} must be [lng, lat] or an object with lat/lng")


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


@router.post("/dispatch")
async def dispatch_route(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    officer: OfficerPrincipal = Depends(require_role("COMMANDER", "DISPATCHER")),
) -> dict:
    """Administrative dispatch action; requires an authenticated command officer."""
    del officer
    return await safe_dispatch_route(payload=payload, db=db)


@router.post("/evacuate")
async def evacuate_route(payload: dict) -> dict:
    """Return an OSRM road corridor that avoids active flood polygons deeper than 0.3m."""
    origin = _coordinate(payload.get("origin"), "origin")
    destination = _coordinate(payload.get("destination"), "destination")
    flood_zones = payload.get(
        "active_flood_zones",
        payload.get("active_flood_zone", payload.get("active_flood_zone_coordinates", [])),
    )
    if "active_flood_zones" not in payload and "active_flood_zone_coordinates" in payload:
        flood_zones = {
            "coordinates": flood_zones,
            "water_depth_m": payload.get("water_depth_m", payload.get("waterDepth", 0)),
        }
    if not isinstance(flood_zones, list):
        flood_zones = [flood_zones]

    try:
        return await evacuation_routing_service.calculate_safe_corridor(
            origin=origin,
            destination=destination,
            flood_zones=flood_zones,
            profile=str(payload.get("profile", "driving")),
        )
    except RoutingError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
