from __future__ import annotations

import logging
from typing import Any

from geoalchemy2 import functions as func
from sqlalchemy import cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spatial_models import FloodPolygon, Incident, SensorGauge

logger = logging.getLogger(__name__)


class NativePostGISService:
    """High-precision PostGIS spatial geofencing, containment, and buffer service."""

    async def check_point_in_polygon(self, lat: float, lng: float, db: AsyncSession) -> list[dict[str, Any]]:
        """Execute PostGIS ST_Contains / ST_Intersects point-in-polygon containment check."""
        point_geom = func.ST_SetSRID(func.ST_Point(lng, lat), 4326)
        query = (
            select(FloodPolygon)
            .where(func.ST_Intersects(FloodPolygon.geom, point_geom))
        )
        try:
            result = await db.execute(query)
            matched_zones = result.scalars().all()
            return [
                {
                    "id": zone.id,
                    "zone_name": zone.zone_name,
                    "depth_m": zone.depth_m,
                    "severity": zone.severity,
                    "risk_score": zone.risk_score,
                }
                for zone in matched_zones
            ]
        except Exception as error:
            logger.warning("PostGIS ST_Intersects query error: %s. Returning fallback.", error)
            return []

    async def check_route_intersection(
        self, coordinates: list[tuple[float, float]], db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Execute PostGIS ST_Intersects line-polygon intersection check for evacuation corridors."""
        if len(coordinates) < 2:
            return []

        points_str = ", ".join(f"{lng} {lat}" for lng, lat in coordinates)
        linestring_wkt = f"LINESTRING({points_str})"
        route_geom = func.ST_GeomFromText(linestring_wkt, 4326)

        query = (
            select(FloodPolygon)
            .where(func.ST_Intersects(FloodPolygon.geom, route_geom))
        )
        try:
            result = await db.execute(query)
            intersected_zones = result.scalars().all()
            return [
                {
                    "id": zone.id,
                    "zone_name": zone.zone_name,
                    "depth_m": zone.depth_m,
                    "risk_score": zone.risk_score,
                }
                for zone in intersected_zones
            ]
        except Exception as error:
            logger.warning("PostGIS route ST_Intersects query error: %s. Returning fallback.", error)
            return []

    async def calculate_river_gauge_buffers(
        self, buffer_meters: float, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Calculate dynamic PostGIS ST_Buffer zones around active river telemetry gauge nodes."""
        query = select(
            SensorGauge.id,
            SensorGauge.sensor_name,
            SensorGauge.water_level_m,
            func.ST_AsGeoJSON(
                func.ST_Buffer(func.ST_SetSRID(func.ST_Point(SensorGauge.lng, SensorGauge.lat), 4326), buffer_meters / 111320.0)
            ).label("buffer_geojson"),
        )
        try:
            result = await db.execute(query)
            buffered_nodes = []
            for item in result.all():
                gauge_id, name, level, geojson = item
                buffered_nodes.append({
                    "id": gauge_id,
                    "sensor_name": name,
                    "water_level_m": level,
                    "buffer_radius_m": buffer_meters,
                    "buffer_geojson": geojson,
                })
            return buffered_nodes
        except Exception as error:
            logger.warning("PostGIS ST_Buffer query error: %s. Returning fallback.", error)
            return []


postgis_service = NativePostGISService()
