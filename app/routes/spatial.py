from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import functions as func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.gis_models import CitizenSOS, InundationZone, IoTWaterGauge, RescueUnit
from app.schemas import GeoJSONFeature, GeoJSONFeatureCollection, NearbySOSQuery

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial"])


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
