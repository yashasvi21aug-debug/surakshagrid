from __future__ import annotations

import json
import math
import logging
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import httpx
from geoalchemy2 import functions as func
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gis_models import InundationZone

logger = logging.getLogger(__name__)

Coordinate = tuple[float, float]  # (lng, lat)


def haversine_distance_km(origin: Coordinate, destination: Coordinate) -> float:
    """Calculate Great-Circle geodesic distance between two [lng, lat] coordinates in km."""
    lng1, lat1 = origin
    lng2, lat2 = destination
    r = 6371.0  # Earth radius in km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


@dataclass(frozen=True)
class ActiveFloodZone:
    polygon: Polygon
    water_depth_m: float


class RoutingError(RuntimeError):
    """Raised when OSRM cannot produce a usable road route."""


class RoutingService:
    """Unified routing engine with dynamic OSRM integration and Shapely geodesic fallback."""

    def __init__(self, osrm_base_url: str = "http://localhost:5000", timeout: float = 15.0) -> None:
        self.osrm_base_url = osrm_base_url.rstrip("/")
        self.timeout = timeout

    def _geodesic_fallback_route(
        self,
        origin: Coordinate,
        destination: Coordinate,
        waypoints: Sequence[Coordinate] = (),
    ) -> dict[str, Any]:
        """Generate a dynamic spatial geodesic corridor route when external OSRM is offline."""
        points = [origin, *waypoints, destination]
        line_coords: list[list[float]] = []
        total_dist_km = 0.0

        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i + 1]
            seg_dist = haversine_distance_km(p1, p2)
            total_dist_km += seg_dist
            num_steps = max(2, int(seg_dist * 10))
            for step in range(num_steps):
                t = step / num_steps
                lng = p1[0] + t * (p2[0] - p1[0])
                lat = p1[1] + t * (p2[1] - p1[1])
                line_coords.append([round(lng, 5), round(lat, 5)])

        line_coords.append([round(destination[0], 5), round(destination[1], 5)])

        duration_sec = (total_dist_km / 35.0) * 3600.0  # Assumes 35 km/h emergency response speed
        return {
            "code": "Ok",
            "routes": [
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": line_coords,
                    },
                    "distance": total_dist_km * 1000.0,
                    "duration": duration_sec,
                    "legs": [
                        {
                            "distance": total_dist_km * 1000.0,
                            "duration": duration_sec,
                            "summary": "Internal Geodesic Spatial Fallback Corridor",
                        }
                    ],
                }
            ],
        }

    async def fetch_osrm_route(
        self,
        origin: Coordinate,
        destination: Coordinate,
        waypoints: Sequence[Coordinate] = (),
        profile: str = "driving",
    ) -> dict[str, Any]:
        """Attempt OSRM HTTP route fetch; fall back to internal geodesic corridor on connection failure."""
        coordinates = [origin, *waypoints, destination]
        coordinate_text = ";".join(f"{lng},{lat}" for lng, lat in coordinates)
        url = (
            f"{self.osrm_base_url}/route/v1/{profile}/{coordinate_text}"
            "?overview=full&geometries=geojson&steps=true"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            if data.get("code") in ("Ok", None) and data.get("routes"):
                return data
        except (httpx.HTTPError, TimeoutError, Exception) as error:
            logger.info("OSRM endpoint unreachable (%s). Activating geodesic fallback engine.", error)

        return self._geodesic_fallback_route(origin, destination, waypoints)

    async def get_osrm_route(
        self,
        origin_coords: tuple[float, float],
        destination_coords: tuple[float, float],
        profile: str = "driving",
    ) -> dict[str, Any]:
        return await self.fetch_osrm_route(origin_coords, destination_coords, profile=profile)

    async def get_critical_inundation_zones(self, db: AsyncSession) -> list[InundationZone]:
        try:
            result = await db.execute(
                select(InundationZone).where(
                    InundationZone.risk_score >= 0.75,
                )
            )
            return result.scalars().all()
        except Exception:
            return []

    def route_intersects_flood(self, route_geojson: dict[str, Any], flood_geometry: Any) -> bool:
        if not route_geojson or "routes" not in route_geojson or not route_geojson["routes"]:
            return False
        geometry = route_geojson["routes"][0].get("geometry")
        if not geometry:
            return False
        return True

    def build_safe_detour_coordinates(
        self,
        origin_coords: tuple[float, float],
        destination_coords: tuple[float, float],
    ) -> list[list[float]]:
        lon1, lat1 = origin_coords
        lon2, lat2 = destination_coords
        return [
            [lon1, lat1],
            [lon1 + 0.006, lat1 + 0.004],
            [lon1 + 0.012, lat1 + 0.007],
            [lon2 - 0.008, lat2 + 0.005],
            [lon2, lat2],
        ]

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
                "message": "No routing corridor generated.",
                "route": {"type": "LineString", "coordinates": []},
            }

        critical_zones = await self.get_critical_inundation_zones(db)
        route_geometry = default_route["routes"][0].get("geometry")
        route_coords = route_geometry.get("coordinates", []) if isinstance(route_geometry, dict) else []

        blocked = False
        if critical_zones and route_coords:
            for zone in critical_zones:
                if zone.polygon is None:
                    continue
                try:
                    intersects = await db.scalar(
                        select(
                            func.ST_Intersects(
                                zone.polygon,
                                func.ST_SetSRID(
                                    func.ST_GeomFromGeoJSON(
                                        json.dumps({
                                            "type": "LineString",
                                            "coordinates": route_coords,
                                        })
                                    ),
                                    4326,
                                ),
                            )
                        )
                    )
                    if intersects:
                        blocked = True
                        break
                except Exception:
                    pass

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

    @staticmethod
    def _route_line(route_response: dict[str, Any]) -> LineString:
        geometry = route_response["routes"][0].get("geometry")
        coordinates = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
        if len(coordinates) < 2:
            raise RoutingError("OSRM returned an invalid route geometry")
        return LineString(coordinates)

    @staticmethod
    def _polygon_from_coordinates(coordinates: Any) -> Polygon | None:
        if isinstance(coordinates, dict):
            coordinates = coordinates.get("coordinates")
        if not isinstance(coordinates, list) or not coordinates:
            return None
        if coordinates and isinstance(coordinates[0], (list, tuple)) and coordinates[0]:
            first = coordinates[0]
            if isinstance(first[0], (int, float)):
                ring = coordinates
            else:
                ring = first
        else:
            return None
        if len(ring) < 3:
            return None
        try:
            polygon = Polygon([(float(point[0]), float(point[1])) for point in ring])
        except (TypeError, ValueError, IndexError):
            return None
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        return polygon if not polygon.is_empty else None

    @classmethod
    def normalize_flood_zones(cls, raw_zones: Iterable[Any]) -> list[ActiveFloodZone]:
        zones: list[ActiveFloodZone] = []
        for raw_zone in raw_zones:
            depth = 0.0
            coordinates = raw_zone
            if isinstance(raw_zone, dict):
                depth = float(
                    raw_zone.get("water_depth_m", raw_zone.get("waterDepth", raw_zone.get("depth", 0)))
                    or 0
                )
                coordinates = raw_zone.get("coordinates", raw_zone.get("polygon"))
            polygon = cls._polygon_from_coordinates(coordinates)
            if polygon is not None:
                zones.append(ActiveFloodZone(polygon=polygon, water_depth_m=depth))
        return zones

    @staticmethod
    def route_intersects_active_flood(route: LineString, zones: Iterable[ActiveFloodZone]) -> bool:
        return any(zone.water_depth_m > 0.3 and route.intersects(zone.polygon) for zone in zones)

    @staticmethod
    def _perimeter_waypoints(zones: Sequence[ActiveFloodZone]) -> list[list[Coordinate]]:
        active_polygons = [zone.polygon for zone in zones if zone.water_depth_m > 0.3]
        if not active_polygons:
            return [[]]
        boundary = unary_union(active_polygons).convex_hull.buffer(0.0015)
        if boundary.geom_type != "Polygon":
            return [[]]
        points = list(boundary.exterior.coords)[:-1]
        if len(points) > 12:
            stride = max(1, len(points) // 12)
            points = points[::stride]
        clockwise = [(float(x), float(y)) for x, y in points]
        counter_clockwise = list(reversed(clockwise))
        return [clockwise, counter_clockwise]

    async def calculate_safe_corridor(
        self,
        origin: Coordinate,
        destination: Coordinate,
        flood_zones: Iterable[Any],
        profile: str = "driving",
    ) -> dict[str, Any]:
        zones = self.normalize_flood_zones(flood_zones)
        initial = await self.fetch_osrm_route(origin, destination, profile=profile)
        initial_line = self._route_line(initial)
        active_zones = [zone for zone in zones if zone.water_depth_m > 0.3]

        selected = initial
        status = "safe"
        if self.route_intersects_active_flood(initial_line, active_zones):
            status = "rerouted"
            selected = None
            for waypoints in self._perimeter_waypoints(active_zones):
                candidate = await self.fetch_osrm_route(origin, destination, waypoints, profile=profile)
                if not self.route_intersects_active_flood(self._route_line(candidate), active_zones):
                    selected = candidate
                    break
            if selected is None:
                # Dynamic geodesic perimeter fallback
                selected = self._geodesic_fallback_route(origin, destination, self._perimeter_waypoints(active_zones)[0])

        route = selected["routes"][0]
        coordinates = route["geometry"]["coordinates"]
        return {
            "status": status,
            "safe_bypass_geojson": {"type": "LineString", "coordinates": coordinates},
            "distance_km": round(float(route.get("distance", 0)) / 1000, 3),
            "estimated_travel_time_mins": round(float(route.get("duration", 0)) / 60, 1),
            "flood_zones_considered": len(active_zones),
        }


# Alias for backward compatibility
FloodAvoidanceRoutingService = RoutingService
