from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.routes.auth import OfficerPrincipal, require_role
from app.services.routing import RoutingError, routing_service

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


def parse_route_coordinates(payload: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float], str]:
    """Parse origin, destination [lng, lat] tuples and profile from flexible payload formats."""
    # Format 1: PRD v1.0.0 explicit start/end fields
    if "start_lat" in payload and "start_lng" in payload and "end_lat" in payload and "end_lng" in payload:
        try:
            o_lat, o_lng = float(payload["start_lat"]), float(payload["start_lng"])
            d_lat, d_lng = float(payload["end_lat"]), float(payload["end_lng"])
            profile = str(payload.get("vehicle_type", payload.get("profile", "driving")))
            return (o_lng, o_lat), (d_lng, d_lat), profile
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=400, detail="Invalid start/end coordinates") from error

    # Format 2: origin and destination [lng, lat] arrays or objects
    origin_raw = payload.get("origin", payload.get("origin_coords"))
    dest_raw = payload.get("destination", payload.get("destination_coords"))

    if origin_raw and dest_raw:
        def _extract(val: Any) -> tuple[float, float]:
            if isinstance(val, dict):
                return float(val.get("lng", val.get("longitude", 0))), float(val.get("lat", val.get("latitude", 0)))
            if isinstance(val, (list, tuple)) and len(val) == 2:
                return float(val[0]), float(val[1])
            raise ValueError("Invalid coordinate format")

        try:
            origin = _extract(origin_raw)
            dest = _extract(dest_raw)
            profile = str(payload.get("profile", payload.get("vehicle_type", "driving")))
            return origin, dest, profile
        except (TypeError, ValueError, IndexError) as error:
            raise HTTPException(status_code=400, detail="Coordinates must be [lng, lat] pairs") from error

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Missing route coordinates. Provide start_lat/start_lng/end_lat/end_lng or origin/destination.",
    )


@router.post("/safe-corridor")
@router.post("/evacuate")
async def safe_corridor_route(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Calculate dynamic flood-evasive routing bypassing submerged road nodes and return GeoJSON LineString."""
    origin, destination, profile = parse_route_coordinates(payload)

    raw_zones = payload.get(
        "active_flood_zones",
        payload.get("active_flood_zone", payload.get("active_flood_zone_coordinates")),
    )
    if not raw_zones:
        flood_zones = await routing_service.get_critical_inundation_zones(db)
    else:
        if isinstance(raw_zones, dict):
            raw_zones = [raw_zones]
        flood_zones = raw_zones

    try:
        return await routing_service.calculate_safe_corridor(
            origin=origin,
            destination=destination,
            flood_zones=flood_zones,
            profile=profile,
        )
    except RoutingError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/safe-dispatch")
async def safe_dispatch_route(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Safe dispatch routing for rescue teams."""
    return await safe_corridor_route(payload=payload, db=db)


@router.post("/dispatch")
async def dispatch_route(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
    officer: OfficerPrincipal = Depends(require_role("COMMANDER", "DISPATCHER")),
) -> dict[str, Any]:
    """Administrative dispatch action; requires an authenticated command officer."""
    del officer
    return await safe_corridor_route(payload=payload, db=db)
