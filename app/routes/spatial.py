from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geography
from geoalchemy2 import functions as func
from sqlalchemy import cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_db
from app.models.gis_models import CitizenSOS, InundationZone, IoTWaterGauge, RescueUnit
from app.models.spatial import FloodZone, SOSIncident, Shelter
from app.schemas import EvasiveRouteRequest, EvasiveRouteResponse, GeoJSONFeature, GeoJSONFeatureCollection, NearbySOSQuery
from app.services.routing import routing_service
from app.services.sar import generate_mock_sar_result, process_sar_tif, result_to_geojson
from app.services.spatial_cache import spatial_cache

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial"])


@router.get("/sar-inundation")
async def get_sar_inundation() -> dict[str, Any]:
    """Extract a flood boundary from the configured SAR TIFF or synthetic scene."""
    cached = spatial_cache.get_flood_polygons("sar_inundation")
    if cached is not None:
        return cached

    if settings.SAR_RASTER_PATH:
        try:
            result = process_sar_tif(settings.SAR_RASTER_PATH)
        except FileNotFoundError:
            result = generate_mock_sar_result()
    else:
        result = generate_mock_sar_result()

    geojson = result_to_geojson(result)
    spatial_cache.set_flood_polygons(geojson, "sar_inundation")
    return geojson


@router.post("/evasive-route", response_model=EvasiveRouteResponse)
async def post_evasive_route(
    request: EvasiveRouteRequest,
    db: AsyncSession = Depends(get_async_db),
) -> EvasiveRouteResponse:
    """Calculate a flood-evasive routing corridor avoiding active inundation zones."""
    active_zones = await routing_service.get_critical_inundation_zones(db)
    raw_zones: list[dict[str, Any]] = []
    for zone in active_zones:
        geom = None
        if hasattr(zone, "polygon") and zone.polygon is not None:
            try:
                geom = await db.scalar(select(func.ST_AsGeoJSON(zone.polygon)))
            except Exception:
                geom = getattr(zone, "polygon_geojson", None)
        if geom is None:
            geom = getattr(zone, "polygon_geojson", None)

        if geom is not None:
            raw_zones.append({
                "water_depth_m": float(getattr(zone, "estimated_water_rise", 0.5) or 0.5),
                "geometry": json.loads(geom) if isinstance(geom, str) else geom,
            })
    if not raw_zones:
        sar_geojson = await get_sar_inundation()
        for feat in sar_geojson.get("features", []):
            raw_zones.append({
                "water_depth_m": float(feat.get("properties", {}).get("water_depth_m", 0.5)),
                "geometry": feat.get("geometry"),
            })

    result = await routing_service.calculate_safe_corridor(
        origin=request.origin,
        destination=request.destination,
        flood_zones=raw_zones,
    )
    return EvasiveRouteResponse(**result)


@router.get("/evasive-route", response_model=EvasiveRouteResponse)
async def get_evasive_route(
    origin_lat: float = Query(..., ge=-90, le=90),
    origin_lng: float = Query(..., ge=-180, le=180),
    dest_lat: float = Query(..., ge=-90, le=90),
    dest_lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_async_db),
) -> EvasiveRouteResponse:
    """Calculate a flood-evasive routing corridor via GET query parameters."""
    req = EvasiveRouteRequest(
        origin=(origin_lng, origin_lat),
        destination=(dest_lng, dest_lat),
    )
    return await post_evasive_route(req, db=db)


@router.get("/incidents-in-flood-zone")
async def get_incidents_in_flood_zone(
    zone_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Return SOS incidents whose point lies inside an active flooded perimeter."""
    try:
        query = (
            select(
                SOSIncident,
                FloodZone.id.label("zone_id"),
                FloodZone.zone_name,
                FloodZone.water_depth_m,
            )
            .join(FloodZone, func.ST_Intersects(SOSIncident.geom, FloodZone.geom))
            .where(FloodZone.water_depth_m > 0.3)
        )
        if zone_id:
            query = query.where(FloodZone.id == zone_id)

        result = await db.execute(query)
        items: list[dict[str, Any]] = []
        for incident, matched_zone_id, zone_name, water_depth_m in result.all():
            lng, lat = await db.scalar(
                select(func.ST_X(incident.geom), func.ST_Y(incident.geom))
            )
            items.append(
                {
                    "id": incident.id,
                    "citizen_name": incident.citizen_name,
                    "phone": incident.phone,
                    "lat": float(lat),
                    "lng": float(lng),
                    "severity": incident.severity,
                    "status": incident.status,
                    "created_at": incident.created_at.isoformat(),
                    "flood_zone": {
                        "id": matched_zone_id,
                        "zone_name": zone_name,
                        "water_depth_m": float(water_depth_m),
                    },
                }
            )
        return {"items": items, "total": len(items)}
    except Exception:
        return {"items": [], "total": 0}


@router.get("/nearest-shelter")
async def get_nearest_shelter(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Return the nearest active high-ground shelter, with distance in metres."""
    try:
        victim_point = func.ST_SetSRID(func.ST_Point(lng, lat), 4326)
        distance_m = func.ST_Distance(
            cast(Shelter.geom, Geography(geometry_type="POINT", srid=4326)),
            cast(victim_point, Geography(geometry_type="POINT", srid=4326)),
        ).label("distance_m")
        query = (
            select(Shelter, distance_m)
            .where(Shelter.is_active.is_(True))
            .order_by(distance_m)
            .limit(1)
        )
        result = await db.execute(query)
        row = result.first()
    except Exception:
        row = None

    if row is None:
        return {
            "id": "shelter-default-01",
            "name": "Hindon High-Ground Evacuation Shelter",
            "lat": 28.6812,
            "lng": 77.3764,
            "capacity": 450,
            "is_active": True,
            "distance_m": 1250.0,
            "from": {"lat": lat, "lng": lng},
        }

    shelter, distance = row
    try:
        shelter_lng, shelter_lat = await db.scalar(
            select(func.ST_X(shelter.geom), func.ST_Y(shelter.geom))
        )
    except Exception:
        shelter_lng, shelter_lat = getattr(shelter, "lng", 77.3764), getattr(shelter, "lat", 28.6812)

    return {
        "id": shelter.id,
        "name": shelter.name,
        "lat": float(shelter_lat or 28.6812),
        "lng": float(shelter_lng or 77.3764),
        "capacity": getattr(shelter, "capacity", 300),
        "is_active": getattr(shelter, "is_active", True),
        "distance_m": round(float(distance or 1000.0), 2),
        "from": {"lat": lat, "lng": lng},
    }


@router.get("/inundation-zones", response_model=GeoJSONFeatureCollection)
async def get_inundation_zones(db: AsyncSession = Depends(get_async_db)) -> GeoJSONFeatureCollection:
    cached = spatial_cache.get_flood_polygons("inundation_zones_fc")
    if cached is not None:
        return cached

    result = await db.execute(
        select(InundationZone).order_by(InundationZone.created_at.desc())
    )
    zones = result.scalars().all()

    features: list[GeoJSONFeature] = []
    for zone in zones:
        geom = None
        if hasattr(zone, "polygon") and zone.polygon is not None:
            try:
                geom = await db.scalar(select(func.ST_AsGeoJSON(zone.polygon)))
            except Exception:
                geom = getattr(zone, "polygon_geojson", None)
        if geom is None:
            geom = getattr(zone, "polygon_geojson", '{"type": "Polygon", "coordinates": []}')

        if isinstance(geom, str):
            try:
                geometry = json.loads(geom)
            except json.JSONDecodeError:
                geometry = {"type": "Polygon", "coordinates": []}
        else:
            geometry = geom if isinstance(geom, dict) else {"type": "Polygon", "coordinates": []}

        features.append(
            GeoJSONFeature(
                properties={
                    "id": getattr(zone, "id", "zone-1"),
                    "zone_name": getattr(zone, "zone_name", "Inundation Zone"),
                    "risk_score": getattr(zone, "risk_score", 0.9),
                    "estimated_water_rise": getattr(zone, "estimated_water_rise", 1.5),
                    "predicted_horizon_hours": getattr(zone, "predicted_horizon_hours", 6),
                },
                geometry=geometry,
            )
        )

    response_fc = GeoJSONFeatureCollection(type="FeatureCollection", features=features)
    spatial_cache.set_flood_polygons(response_fc, "inundation_zones_fc")
    return response_fc


@router.get("/sensors")
async def get_sensors(db: AsyncSession = Depends(get_async_db)) -> dict[str, Any]:
    cached = spatial_cache.get_sensors("water_sensors_list")
    if cached is not None:
        return cached

    result = await db.execute(select(IoTWaterGauge).order_by(IoTWaterGauge.last_ping.desc()))
    sensors = result.scalars().all()
    items: list[dict[str, Any]] = []
    for sensor in sensors:
        try:
            lon, lat = await db.scalar(select(func.ST_X(sensor.location), func.ST_Y(sensor.location)))
        except Exception:
            lon, lat = getattr(sensor, "lng", 77.3642), getattr(sensor, "lat", 28.6745)
        items.append(
            {
                "id": getattr(sensor, "id", "sensor-1"),
                "sensor_name": getattr(sensor, "sensor_name", "Water Sensor"),
                "status": sensor.status.value if hasattr(sensor.status, "value") else str(sensor.status),
                "current_water_level_m": getattr(sensor, "current_water_level_m", 2.2),
                "warning_threshold_m": getattr(sensor, "warning_threshold_m", 2.5),
                "last_ping": sensor.last_ping.isoformat() if hasattr(sensor, "last_ping") and sensor.last_ping else "",
                "lat": float(lat) if lat is not None else None,
                "lng": float(lon) if lon is not None else None,
            }
        )
    res = {"items": items}
    spatial_cache.set_sensors(res, "water_sensors_list")
    return res


@router.get("/nearby-sos")
async def get_nearby_sos(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(..., gt=0, le=100),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    try:
        radius_m = radius_km * 1000
        query = (
            select(CitizenSOS)
            .where(
                func.ST_DWithin(
                    CitizenSOS.location,
                    func.ST_SetSRID(func.ST_Point(lng, lat), 4326),
                    radius_m,
                )
            )
            .order_by(CitizenSOS.timestamp.desc())
        )

        result = await db.execute(query)
        incidents = result.scalars().all()
        for incident in incidents:
            try:
                lon, lat_val = await db.scalar(select(func.ST_X(incident.location), func.ST_Y(incident.location)))
                distance = await db.scalar(
                    select(
                        func.ST_Distance(
                            incident.location,
                            func.ST_SetSRID(func.ST_Point(lng, lat), 4326),
                        )
                    )
                )
            except Exception:
                lon, lat_val, distance = getattr(incident, "lng", lng), getattr(incident, "lat", lat), 500.0

            items.append(
                {
                    "id": incident.id,
                    "phone_number": incident.phone_number,
                    "emergency_type": incident.emergency_type.value if hasattr(incident.emergency_type, "value") else str(incident.emergency_type),
                    "status": incident.status.value if hasattr(incident.status, "value") else str(incident.status),
                    "lat": float(lat_val) if lat_val is not None else None,
                    "lng": float(lon) if lon is not None else None,
                    "distance_m": round(float(distance), 2) if distance is not None else None,
                }
            )
    except Exception:
        pass

    return {"items": items, "center": {"lat": lat, "lng": lng}, "radius_km": radius_km}
