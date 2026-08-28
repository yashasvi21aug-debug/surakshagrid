from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geography
from geoalchemy2 import functions as func
from sqlalchemy import cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.gis_models import CitizenSOS, InundationZone, IoTWaterGauge, RescueUnit
from app.models.spatial import FloodZone, SOSIncident, Shelter
from app.schemas import GeoJSONFeature, GeoJSONFeatureCollection, NearbySOSQuery
from app.config import settings
from app.services.sar import generate_mock_sar_result, process_sar_tif, result_to_geojson

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial"])


@router.get("/sar-inundation")
async def get_sar_inundation() -> dict[str, Any]:
    """Extract a flood boundary from the configured SAR TIFF or synthetic scene."""
    if settings.SAR_RASTER_PATH:
        try:
            result = process_sar_tif(settings.SAR_RASTER_PATH)
        except FileNotFoundError:
            result = generate_mock_sar_result()
    else:
        result = generate_mock_sar_result()
    return result_to_geojson(result)


@router.get("/incidents-in-flood-zone")
async def get_incidents_in_flood_zone(
    zone_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return SOS incidents whose point lies inside an active flooded perimeter."""
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


@router.get("/nearest-shelter")
async def get_nearest_shelter(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the nearest active high-ground shelter, with distance in metres."""
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
    if row is None:
        raise HTTPException(status_code=404, detail="No active shelter found")

    shelter, distance = row
    shelter_lng, shelter_lat = await db.scalar(
        select(func.ST_X(shelter.geom), func.ST_Y(shelter.geom))
    )
    return {
        "id": shelter.id,
        "name": shelter.name,
        "lat": float(shelter_lat),
        "lng": float(shelter_lng),
        "capacity": shelter.capacity,
        "is_active": shelter.is_active,
        "distance_m": round(float(distance), 2),
        "from": {"lat": lat, "lng": lng},
    }


@router.get("/inundation-zones", response_model=GeoJSONFeatureCollection)
async def get_inundation_zones(db: AsyncSession = Depends(get_db)) -> GeoJSONFeatureCollection:
    result = await db.execute(
        select(InundationZone).order_by(InundationZone.created_at.desc())
    )
    zones = result.scalars().all()

    features: list[GeoJSONFeature] = []
    for zone in zones:
        geom = await db.scalar(select(func.ST_AsGeoJSON(zone.polygon)))
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
                    "id": zone.id,
                    "zone_name": zone.zone_name,
                    "risk_score": zone.risk_score,
                    "estimated_water_rise": zone.estimated_water_rise,
                    "predicted_horizon_hours": zone.predicted_horizon_hours,
                },
                geometry=geometry,
            )
        )

    return GeoJSONFeatureCollection(type="FeatureCollection", features=features)


@router.get("/sensors")
async def get_sensors(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(IoTWaterGauge).order_by(IoTWaterGauge.last_ping.desc()))
    sensors = result.scalars().all()
    items: list[dict[str, Any]] = []
    for sensor in sensors:
        lon, lat = await db.scalar(select(func.ST_X(sensor.location), func.ST_Y(sensor.location)))
        items.append(
            {
                "id": sensor.id,
                "sensor_name": sensor.sensor_name,
                "status": sensor.status.value,
                "current_water_level_m": sensor.current_water_level_m,
                "warning_threshold_m": sensor.warning_threshold_m,
                "last_ping": sensor.last_ping.isoformat(),
                "lat": float(lat) if lat is not None else None,
                "lng": float(lon) if lon is not None else None,
            }
        )
    return {"items": items}


@router.get("/nearby-sos")
async def get_nearby_sos(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(..., gt=0, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
    items: list[dict[str, Any]] = []
    for incident in incidents:
        lon, lat_val = await db.scalar(select(func.ST_X(incident.location), func.ST_Y(incident.location)))
        distance = await db.scalar(
            select(
                func.ST_Distance(
                    incident.location,
                    func.ST_SetSRID(func.ST_Point(lng, lat), 4326),
                )
            )
        )
        items.append(
            {
                "id": incident.id,
                "phone_number": incident.phone_number,
                "emergency_type": incident.emergency_type.value,
                "status": incident.status.value,
                "lat": float(lat_val) if lat_val is not None else None,
                "lng": float(lon) if lon is not None else None,
                "distance_m": round(float(distance), 2) if distance is not None else None,
            }
        )
    return {"items": items, "center": {"lat": lat, "lng": lng}, "radius_km": radius_km}
