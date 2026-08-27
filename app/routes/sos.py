from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import functions as func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.gis_models import CitizenSOS, CitizenStatus, EmergencyType
from app.schemas import NearbySOSQuery, SOSCreateRequest, SOSListQuery, SOSResponse, SOSStatusUpdate
from app.websocket_manager import manager

router = APIRouter(prefix="/api/v1/sos", tags=["sos"])


@router.post("/", response_model=SOSResponse, status_code=status.HTTP_201_CREATED)
async def create_sos(
    payload: SOSCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> SOSResponse:
    point_wkt = func.ST_SetSRID(func.ST_Point(payload.lng, payload.lat), 4326)
    incident = CitizenSOS(
        phone_number=payload.phone,
        emergency_type=payload.emergencyType,
        location=point_wkt,
        rain_rate=payload.rainRate,
        risk_status="MEDIUM" if payload.rainRate and payload.rainRate > 25 else "LOW",
        status=CitizenStatus.PENDING,
    )

    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    incident_payload = {
        "event": "new_sos",
        "data": {
            "id": incident.id,
            "phone_number": incident.phone_number,
            "emergency_type": incident.emergency_type.value,
            "lat": payload.lat,
            "lng": payload.lng,
            "rain_rate": incident.rain_rate,
            "risk_status": incident.risk_status,
            "status": incident.status.value,
            "timestamp": incident.timestamp.isoformat(),
        },
    }
    await manager.broadcast(incident_payload)

    return SOSResponse(
        id=incident.id,
        phone_number=incident.phone_number,
        emergency_type=incident.emergency_type.value,
        lat=payload.lat,
        lng=payload.lng,
        rain_rate=incident.rain_rate,
        risk_status=incident.risk_status,
        status=incident.status.value,
        timestamp=incident.timestamp.isoformat(),
    )


@router.get("/", response_model=dict[str, Any])
async def list_sos(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    min_lng: float | None = Query(default=None, ge=-180, le=180),
    max_lng: float | None = Query(default=None, ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(CitizenSOS)
    if min_lat is not None:
        stmt = stmt.where(func.ST_Y(CitizenSOS.location) >= min_lat)
    if max_lat is not None:
        stmt = stmt.where(func.ST_Y(CitizenSOS.location) <= max_lat)
    if min_lng is not None:
        stmt = stmt.where(func.ST_X(CitizenSOS.location) >= min_lng)
    if max_lng is not None:
        stmt = stmt.where(func.ST_X(CitizenSOS.location) <= max_lng)

    stmt = stmt.order_by(CitizenSOS.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    incidents = result.scalars().all()

    items = []
    for incident in incidents:
        lon, lat = await db.scalar(
            select(func.ST_X(incident.location), func.ST_Y(incident.location))
        )
        if lon is None or lat is None:
            continue
        items.append(
            {
                "id": incident.id,
                "phone_number": incident.phone_number,
                "emergency_type": incident.emergency_type.value,
                "lat": float(lat),
                "lng": float(lon),
                "rain_rate": incident.rain_rate,
                "risk_status": incident.risk_status,
                "status": incident.status.value,
                "timestamp": incident.timestamp.isoformat(),
            }
        )

    total_stmt = select(func.count()).select_from(CitizenSOS)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.patch("/{id}/status")
async def update_sos_status(
    id: str,
    payload: SOSStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    incident = await db.get(CitizenSOS, id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SOS incident not found")

    incident.status = payload.status
    await db.commit()
    await db.refresh(incident)

    event = {
        "event": "sos_status_update",
        "data": {
            "id": incident.id,
            "status": incident.status.value,
            "phone_number": incident.phone_number,
            "emergency_type": incident.emergency_type.value,
        },
    }
    await manager.broadcast(event)

    return {"id": incident.id, "status": incident.status.value}
