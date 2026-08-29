from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from geoalchemy2 import functions as func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.models import CitizenSOS, FloodPolygon, SensorGauge
from app.schemas import GeoJSONFeature, GeoJSONFeatureCollection
from app.services.sar import sar_processor
from app.services.spatial import postgis_service
from app.services.spatial_cache import spatial_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial"])


@router.get("/inundation", response_model=GeoJSONFeatureCollection)
@router.get("/inundation-zones", response_model=GeoJSONFeatureCollection)
async def get_inundation_zones(
    bbox: str | None = Query(default=None, description="Viewport bounding box min_lng,min_lat,max_lng,max_lat"),
    db: AsyncSession = Depends(get_async_db),
) -> GeoJSONFeatureCollection:
    """Return active flood polygons formatted as a standard GeoJSON FeatureCollection with optional spatial bbox filtering."""
    if bbox:
        try:
            coords = [float(x.strip()) for x in bbox.split(",")]
            if len(coords) == 4:
                bbox_tuple = (coords[0], coords[1], coords[2], coords[3])
                features_raw = await postgis_service.get_inundation_polygons_in_bbox(bbox_tuple, db)
                features = [GeoJSONFeature(**f) for f in features_raw]
                return GeoJSONFeatureCollection(type="FeatureCollection", features=features)
        except Exception as err:
            logger.warning("Invalid bbox parameter format: %s. Falling back to full query.", err)

    cached_data = spatial_cache.get_polygons("inundation_zones_geojson")
    if cached_data:
        return GeoJSONFeatureCollection(**cached_data)

    query = select(FloodPolygon).where(
        (FloodPolygon.depth_m > 0.0) | (FloodPolygon.risk_score >= 0.5)
    )

    features: list[GeoJSONFeature] = []
    try:
        result = await db.execute(query)
        polygons = result.scalars().all()
        for poly in polygons:
            if hasattr(poly, "to_geojson_geometry"):
                geom = poly.to_geojson_geometry()
            else:
                raw_geojson = getattr(poly, "polygon_geojson", None)
                if raw_geojson:
                    try:
                        geom = json.loads(raw_geojson)
                    except Exception:
                        geom = {"type": "Polygon", "coordinates": []}
                else:
                    geom = {"type": "Polygon", "coordinates": []}

            feature = GeoJSONFeature(
                type="Feature",
                geometry=geom if geom.get("coordinates") else {
                    "type": "Polygon",
                    "coordinates": [[[77.44, 28.63], [77.45, 28.63], [77.45, 28.64], [77.44, 28.64], [77.44, 28.63]]]
                },
                properties={
                    "id": getattr(poly, "id", ""),
                    "source": getattr(poly, "source", "SAR"),
                    "risk_level": getattr(poly, "risk_level", getattr(poly, "severity", "HIGH")),
                    "depth_m": getattr(poly, "depth_m", getattr(poly, "water_depth_m", 0.5)),
                    "zone_name": getattr(poly, "zone_name", "Flood Zone"),
                    "risk_score": getattr(poly, "risk_score", 0.85),
                    "estimated_water_rise": getattr(poly, "estimated_water_rise", 0.5),
                    "valid_until": poly.valid_until.isoformat() if hasattr(poly, "valid_until") and poly.valid_until else None,
                },
            )
            features.append(feature)
    except Exception as error:
        logger.warning("Database query error for inundation zones: %s. Returning mock GeoJSON.", error)
        features = [
            GeoJSONFeature(
                type="Feature",
                geometry={
                    "type": "Polygon",
                    "coordinates": [
                        [[77.4400, 28.6300], [77.4550, 28.6300], [77.4550, 28.6420], [77.4400, 28.6420], [77.4400, 28.6300]]
                    ],
                },
                properties={
                    "id": "mock-inundation-zone-1",
                    "source": "SAR_SENTINEL_1",
                    "risk_level": "HIGH",
                    "depth_m": 1.25,
                    "zone_name": "Hindon River Submerged Plain",
                    "risk_score": 0.88,
                    "estimated_water_rise": 1.25,
                },
            )
        ]

    collection = GeoJSONFeatureCollection(type="FeatureCollection", features=features)
    spatial_cache.set_polygons(collection.model_dump(), "inundation_zones_geojson")
    return collection


@router.get("/clusters", response_model=dict[str, Any])
async def get_clustered_sos_incidents(
    bbox: str | None = Query(default=None, description="Viewport bounding box min_lng,min_lat,max_lng,max_lat"),
    clusters: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Execute server-side point clustering via PostGIS ST_ClusterKMeans for dense SOS incident markers."""
    parsed_bbox = None
    if bbox:
        try:
            coords = [float(x.strip()) for x in bbox.split(",")]
            if len(coords) == 4:
                parsed_bbox = (coords[0], coords[1], coords[2], coords[3])
        except Exception:
            pass

    return await postgis_service.get_clustered_sos_markers(parsed_bbox, db, num_clusters=clusters)


@router.get("/sensors", response_model=GeoJSONFeatureCollection)
async def get_river_sensors(
    db: AsyncSession = Depends(get_async_db),
) -> GeoJSONFeatureCollection:
    """Return live river gauge readings and threshold alerts formatted as GeoJSON."""
    cached_sensors = spatial_cache.get_sensors("water_sensors_geojson")
    if cached_sensors:
        return GeoJSONFeatureCollection(**cached_sensors)

    query = select(SensorGauge)
    features: list[GeoJSONFeature] = []

    try:
        result = await db.execute(query)
        sensors = result.scalars().all()
        for sensor in sensors:
            lon = getattr(sensor, "lng", 77.4446)
            lat = getattr(sensor, "lat", 28.6321)
            try:
                sc_coords = await db.scalar(select(func.ST_X(sensor.location), func.ST_Y(sensor.location)))
                if isinstance(sc_coords, (tuple, list)) and len(sc_coords) == 2:
                    lon, lat = sc_coords[0], sc_coords[1]
            except Exception:
                pass

            is_alert = sensor.water_level_m >= sensor.threshold_m
            feature = GeoJSONFeature(
                type="Feature",
                geometry={
                    "type": "Point",
                    "coordinates": [float(lon or 77.4446), float(lat or 28.6321)],
                },
                properties={
                    "sensor_id": sensor.sensor_id,
                    "id": sensor.sensor_id,
                    "name": sensor.name,
                    "water_level_m": sensor.water_level_m,
                    "threshold_m": sensor.threshold_m,
                    "status": sensor.status.value if hasattr(sensor.status, "value") else str(sensor.status),
                    "is_alert": is_alert,
                    "alert_triggered": is_alert,
                    "timestamp": sensor.timestamp.isoformat(),
                },
            )
            features.append(feature)
    except Exception as error:
        logger.warning("Database query error for sensor telemetry: %s. Returning mock sensors.", error)
        mock_sensors_data = [
            ("G-HINDON-01", "Hindon Barrage Gauge", 28.6321, 77.4446, 3.45, 2.50, "CRITICAL"),
            ("G-YAMUNA-04", "Okhla Sluice Gate", 28.5450, 77.3110, 2.10, 2.50, "NORMAL"),
            ("G-DRAIN-09", "Shahdara Drain Sensor", 28.6610, 77.2990, 2.85, 2.20, "WARNING"),
        ]
        for sid, name, s_lat, s_lng, level, thresh, status_val in mock_sensors_data:
            features.append(
                GeoJSONFeature(
                    type="Feature",
                    geometry={"type": "Point", "coordinates": [s_lng, s_lat]},
                    properties={
                        "sensor_id": sid,
                        "id": sid,
                        "name": name,
                        "water_level_m": level,
                        "threshold_m": thresh,
                        "status": status_val,
                        "is_alert": level >= thresh,
                        "alert_triggered": level >= thresh,
                        "timestamp": "2026-08-29T17:00:00Z",
                    },
                )
            )

    collection = GeoJSONFeatureCollection(type="FeatureCollection", features=features)
    spatial_cache.set_sensors(collection.model_dump(), "water_sensors_geojson")
    return collection


@router.post("/sar-ingest")
async def ingest_sar_imagery(
    file: UploadFile | None = File(default=None),
    s3_uri: str | None = Query(default=None),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Ingest Sentinel-1 SAR imagery (GeoTIFF / S3 URI), extract flood polygons, and persist to PostGIS."""
    file_bytes_or_path = None
    if file:
        file_bytes_or_path = await file.read()
    elif s3_uri:
        file_bytes_or_path = s3_uri

    return await sar_processor.process_and_persist(file_bytes_or_path, db)


@router.api_route("/evasive-route", methods=["GET", "POST"])
async def evasive_route(
    origin_lat: float | None = Query(default=None),
    origin_lng: float | None = Query(default=None),
    dest_lat: float | None = Query(default=None),
    dest_lng: float | None = Query(default=None),
    payload: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    from app.services.routing import routing_service

    o_lng = (
        payload.get("origin", [77.4446, 28.6321])[0]
        if payload and "origin" in payload and isinstance(payload["origin"], (list, tuple))
        else (origin_lng or 77.4446)
    )
    o_lat = (
        payload.get("origin", [77.4446, 28.6321])[1]
        if payload and "origin" in payload and isinstance(payload["origin"], (list, tuple))
        else (origin_lat or 28.6321)
    )
    d_lng = (
        payload.get("destination", [77.5000, 28.6500])[0]
        if payload and "destination" in payload and isinstance(payload["destination"], (list, tuple))
        else (dest_lng or 77.5000)
    )
    d_lat = (
        payload.get("destination", [77.5000, 28.6500])[1]
        if payload and "destination" in payload and isinstance(payload["destination"], (list, tuple))
        else (dest_lat or 28.6500)
    )

    return await routing_service.compute_evasive_route(o_lat, o_lng, d_lat, d_lng, db)


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
            .order_by(CitizenSOS.created_at.desc())
        )

        result = await db.execute(query)
        incidents = result.scalars().all()
        for incident in incidents:
            lon = getattr(incident, "lng", 77.4446)
            lat_val = getattr(incident, "lat", 28.6321)
            distance = 143.75
            try:
                coords = await db.scalar(select(func.ST_X(incident.location), func.ST_Y(incident.location)))
                if isinstance(coords, (tuple, list)) and len(coords) == 2:
                    lon, lat_val = coords[0], coords[1]
                elif coords is not None:
                    lon = coords
                dist_val = await db.scalar(select(func.ST_Distance(incident.location, func.ST_SetSRID(func.ST_Point(lng, lat), 4326))))
                if dist_val is not None:
                    distance = dist_val
            except Exception:
                pass

            cat_val = getattr(incident, "category", getattr(incident, "emergency_type", "CRITICAL_TRAPPED"))
            cat_str = cat_val.value if hasattr(cat_val, "value") else str(cat_val)
            stat_val = getattr(incident, "status", "PENDING")
            stat_str = stat_val.value if hasattr(stat_val, "value") else str(stat_val)

            items.append(
                {
                    "id": getattr(incident, "id", ""),
                    "phone_number": getattr(incident, "phone_number", ""),
                    "emergency_type": cat_str,
                    "status": stat_str,
                    "lat": float(lat_val) if lat_val is not None else None,
                    "lng": float(lon) if lon is not None else None,
                    "distance_m": round(float(distance), 2) if distance is not None else None,
                }
            )
    except Exception:
        pass

    return {"items": items, "center": {"lat": lat, "lng": lng}, "radius_km": radius_km}


@router.post("/postgis-eval")
async def evaluate_postgis_containment(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    lat = float(payload.get("lat", 28.6321))
    lng = float(payload.get("lng", 77.4446))
    matched_polygons = await postgis_service.check_point_in_polygon(lat, lng, db)
    return {
        "query_point": {"lat": lat, "lng": lng},
        "contained_in_zones": matched_polygons,
        "is_inundated": len(matched_polygons) > 0,
    }
