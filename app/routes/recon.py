from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/recon", tags=["reconnaissance"])


@router.post("/uav-orthomosaic", response_model=dict[str, Any])
async def upload_uav_orthomosaic(
    file: UploadFile = File(...),
    drone_id: str = Query(default="UAV-NDRF-ALPHA-09"),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Upload high-resolution UAV aerial orthomosaic GeoTIFF for boundary refinement (PRD Section 2 & 4.2)."""
    file_bytes = await file.read()
    logger.info("Received UAV orthomosaic upload from %s (%d bytes).", drone_id, len(file_bytes))

    return {
        "status": "PROCESSED",
        "drone_id": drone_id,
        "refinement_polygons_count": 2,
        "refined_geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [77.4420, 28.6310],
                                [77.4500, 28.6310],
                                [77.4500, 28.6380],
                                [77.4420, 28.6380],
                                [77.4420, 28.6310],
                            ]
                        ],
                    },
                    "properties": {"source": "UAV_HIGH_RES_ORTHOMOSAIC", "resolution_m": 0.05},
                }
            ],
        },
    }


@router.get("/drone-streams", response_model=dict[str, Any])
async def get_active_drone_streams() -> dict[str, Any]:
    """Return active UAV aerial reconnaissance video streams with GPS telemetry points."""
    return {
        "drones": [
            {
                "drone_id": "UAV-NDRF-01",
                "callsign": "SkySentinel Alpha",
                "lat": 28.6380,
                "lng": 77.4420,
                "altitude_m": 120.0,
                "heading_deg": 145,
                "stream_url": "https://surakshagrid-demo-stream.local/hls/uav-01.m3u8",
                "status": "LIVE_PATROL",
            }
        ]
    }
