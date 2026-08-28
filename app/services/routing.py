from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import httpx
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


Coordinate = tuple[float, float]


@dataclass(frozen=True)
class ActiveFloodZone:
    polygon: Polygon
    water_depth_m: float


class RoutingError(RuntimeError):
    """Raised when OSRM cannot produce a usable road route."""


class FloodAvoidanceRoutingService:
    """Build OSRM routes and reject trajectories through active flood polygons."""

    def __init__(self, osrm_base_url: str = "http://localhost:5000", timeout: float = 15.0) -> None:
        self.osrm_base_url = osrm_base_url.rstrip("/")
        self.timeout = timeout

    async def fetch_osrm_route(
        self,
        origin: Coordinate,
        destination: Coordinate,
        waypoints: Sequence[Coordinate] = (),
        profile: str = "driving",
    ) -> dict[str, Any]:
        coordinates = [origin, *waypoints, destination]
        coordinate_text = ";".join(f"{lng},{lat}" for lng, lat in coordinates)
        url = (
            f"{self.osrm_base_url}/route/v1/{profile}/{coordinate_text}"
            "?overview=full&geometries=geojson&steps=false"
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        if data.get("code") not in (None, "Ok") or not data.get("routes"):
            raise RoutingError("OSRM returned no route for the supplied coordinates")
        return data

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
        # Accept either a GeoJSON Polygon coordinate array or one linear ring.
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
        # A small geographic buffer places waypoints outside the flood boundary.
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
                raise RoutingError("OSRM could not produce a corridor outside the active flood zones")

        route = selected["routes"][0]
        coordinates = route["geometry"]["coordinates"]
        return {
            "status": status,
            "safe_bypass_geojson": {"type": "LineString", "coordinates": coordinates},
            "distance_km": round(float(route.get("distance", 0)) / 1000, 3),
            "estimated_travel_time_mins": round(float(route.get("duration", 0)) / 60, 1),
            "flood_zones_considered": len(active_zones),
        }
