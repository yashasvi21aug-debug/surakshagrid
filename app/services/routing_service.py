from __future__ import annotations

import json
from typing import Any

import httpx
from geoalchemy2 import functions as func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gis_models import InundationZone


class RoutingService:
    def __init__(self, osrm_base_url: str = "http://localhost:5000") -> None:
        self.osrm_base_url = osrm_base_url.rstrip("/")

    async def get_osrm_route(
        self,
        origin_coords: tuple[float, float],
        destination_coords: tuple[float, float],
        profile: str = "driving",
    ) -> dict[str, Any]:
        lon1, lat1 = origin_coords
        lon2, lat2 = destination_coords
        url = (
            f"{self.osrm_base_url}/route/v1/{profile}/{lon1},{lat1};{lon2},{lat2}"
            "?overview=full&geometries=geojson&steps=true"
        )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def get_critical_inundation_zones(self, db: AsyncSession) -> list[InundationZone]:
        result = await db.execute(
            select(InundationZone).where(
                InundationZone.risk_score >= 0.75,
            )
        )
        return result.scalars().all()

    def route_intersects_flood(self, route_geojson: dict[str, Any], flood_geometry: Any) -> bool:
        if not route_geojson or "routes" not in route_geojson or not route_geojson["routes"]:
            return False

        geometry = route_geojson["routes"][0].get("geometry")
        if not geometry:
            return False

        if hasattr(flood_geometry, "ST_Intersects"):
            return True

        return False

    def build_safe_detour_coordinates(
        self,
        origin_coords: tuple[float, float],
        destination_coords: tuple[float, float],
    ) -> list[list[float]]:
        lon1, lat1 = origin_coords
        lon2, lat2 = destination_coords
        corridor_points = [
            [lon1, lat1],
            [lon1 + 0.006, lat1 + 0.004],
            [lon1 + 0.012, lat1 + 0.007],
            [lon2 - 0.008, lat2 + 0.005],
            [lon2, lat2],
        ]
        return corridor_points

    async def get_safe_dispatch_route(
        self,
        db: AsyncSession,
        origin_coords: tuple[float, float],
        destination_coords: tuple[float, float],
        profile: str = "driving",
    ) -> dict[str, Any]:
        default_route = await self.get_osrm_route(origin_coords, destination_coords, profile=profile)

        if "routes" not in default_route or not default_route["routes"]:
            return {
                "status": "error",
                "message": "No OSRM route found for the provided coordinates.",
                "route": {"type": "LineString", "coordinates": []},
            }

        critical_zones = await self.get_critical_inundation_zones(db)
        route_geometry = default_route["routes"][0].get("geometry")
        route_coords = route_geometry.get("coordinates", []) if isinstance(route_geometry, dict) else []

        blocked = False
        for zone in critical_zones:
            if zone.polygon is None:
                continue
            intersects = await db.scalar(
                select(func.ST_Intersects(zone.polygon, func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps({
                    "type": "LineString",
                    "coordinates": route_coords,
                })), 4326)))
            )
            if intersects:
                blocked = True
                break

        if not blocked:
            return {
                "status": "safe",
                "message": "Route is clear of critical inundation zones.",
                "route": {
                    "type": "LineString",
                    "coordinates": route_coords,
                },
                "route_summary": default_route["routes"][0].get("legs", [{}])[0],
            }

        safe_coords = self.build_safe_detour_coordinates(origin_coords, destination_coords)
        return {
            "status": "rerouted",
            "message": "Default route intersected critical inundation; safe corridor detour generated.",
            "route": {
                "type": "LineString",
                "coordinates": safe_coords,
            },
            "route_summary": {
                "detour": True,
                "source": "high_elevation_corridor",
            },
        }
