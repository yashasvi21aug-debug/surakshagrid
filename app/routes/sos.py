from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from geoalchemy2 import functions as func
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.middleware.security import sanitize_gps_telemetry
from app.models import CitizenSOS, CitizenStatus, EmergencyType
from app.schemas import SOSCreateRequest, SOSResponse, SOSStatusUpdate
from app.websocket_manager import manager

router = APIRouter(prefix="/api/v1/sos", tags=["sos"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/", response_model=SOSResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_sos(
    request: Request,
    payload: SOSCreateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> SOSResponse:
    """Trigger a new citizen emergency SOS alert, validate GPS bounds, persist PostGIS record, and broadcast event."""
    raw_lat = payload.latitude if payload.latitude is not None else (payload.lat if payload.lat is not None else 28.6321)
    raw_lng = payload.longitude if payload.longitude is not None else (payload.lng if payload.lng is not None else 77.4446)

    # Sanitize and validate GPS bounds & accuracy telemetry
    lat, lng, accuracy = sanitize_gps_telemetry(raw_lat, raw_lng, payload.accuracy)

    phone_no = payload.phone or "+919876543210"
    cat = payload.category or payload.emergencyType or EmergencyType.CRITICAL_TRAPPED

    point_wkt = func.ST_SetSRID(func.ST_Point(lng, lat), 4326)
    incident = CitizenSOS(
        category=cat,
        status=CitizenStatus.PENDING,
        location=point_wkt,
        accuracy=accuracy,
        notes=payload.notes,
        phone_number=phone_no,
        lat=lat,
        lng=lng,
        rain_rate=payload.rainRate,
        risk_status="MEDIUM" if payload.rainRate and payload.rainRate > 25 else "LOW",
    )

    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    incident_data = {
        "id": incident.id,
        "phone_number": incident.phone_number,
        "category": incident.category.value if hasattr(incident.category, "value") else str(incident.category),
        "emergency_type": incident.category.value if hasattr(incident.category, "value") else str(incident.category),
        "lat": lat,
        "lng": lng,
        "accuracy": incident.accuracy,
        "notes": incident.notes,
        "rain_rate": incident.rain_rate,
        "risk_status": incident.risk_status,
        "status": incident.status.value if hasattr(incident.status, "value") else str(incident.status),
        "timestamp": incident.timestamp.isoformat(),
    }

    # Low-latency broadcast to connected dispatchers and command centers
    await manager.broadcast_sos(incident_data)

    return SOSResponse(
        id=incident.id,
        phone_number=incident.phone_number,
        emergency_type=incident_data["emergency_type"],
        lat=lat,
        lng=lng,
        rain_rate=incident.rain_rate,
        risk_status=incident.risk_status,
        status=incident_data["status"],
        timestamp=incident.timestamp.isoformat(),
    )


@router.post("/{id}/acknowledge")
async def acknowledge_sos(
    id: str,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Acknowledge & dispatch rescue response for an active SOS incident."""
    incident = await db.get(CitizenSOS, id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SOS incident not found")

    incident.status = CitizenStatus.DISPATCHED
    await db.commit()
    await db.refresh(incident)

    event = {
        "event": "sos_acknowledged",
        "type": "SOS_ACKNOWLEDGED",
        "data": {
            "id": incident.id,
            "status": incident.status.value if hasattr(incident.status, "value") else str(incident.status),
            "phone_number": incident.phone_number,
            "emergency_type": incident.category.value if hasattr(incident.category, "value") else str(incident.category),
        },
    }
    await manager.broadcast_to_rooms(event, ["dashboard", "responders", "citizens"])
    return {"id": incident.id, "status": event["data"]["status"], "message": "Incident acknowledged and dispatched."}


@router.post("/{id}/resolve")
async def resolve_sos(
    id: str,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Mark an active SOS incident as resolved / rescued."""
    incident = await db.get(CitizenSOS, id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SOS incident not found")

    incident.status = CitizenStatus.RESOLVED
    await db.commit()
    await db.refresh(incident)

    event = {
        "event": "sos_resolved",
        "type": "SOS_RESOLVED",
        "data": {
            "id": incident.id,
            "status": incident.status.value if hasattr(incident.status, "value") else str(incident.status),
            "phone_number": incident.phone_number,
            "emergency_type": incident.category.value if hasattr(incident.category, "value") else str(incident.category),
        },
    }
    await manager.broadcast_to_rooms(event, ["dashboard", "responders", "citizens"])
    return {"id": incident.id, "status": event["data"]["status"], "message": "Incident successfully resolved."}


@router.get("/", response_model=dict[str, Any])
async def list_sos(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    min_lng: float | None = Query(default=None, ge=-180, le=180),
    max_lng: float | None = Query(default=None, ge=-180, le=180),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """List SOS incidents with spatial bounding box filtering and pagination."""
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
        lon, lat = incident.lng, incident.lat
        try:
            coords = await db.scalar(select(func.ST_X(incident.location), func.ST_Y(incident.location)))
            if isinstance(coords, (tuple, list)) and len(coords) == 2:
                lon, lat = coords[0], coords[1]
        except Exception:
            pass

        if lon is None or lat is None:
            continue
        items.append(
            {
                "id": incident.id,
                "phone_number": incident.phone_number,
                "emergency_type": incident.category.value if hasattr(incident.category, "value") else str(incident.category),
                "lat": float(lat),
                "lng": float(lon),
                "rain_rate": incident.rain_rate,
                "risk_status": incident.risk_status,
                "status": incident.status.value if hasattr(incident.status, "value") else str(incident.status),
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
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Update status for backward compatibility."""
    incident = await db.get(CitizenSOS, id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SOS incident not found")

    incident.status = payload.status
    await db.commit()
    await db.refresh(incident)

    stat_str = incident.status.value if hasattr(incident.status, "value") else str(incident.status)
    event = {
        "event": "sos_status_update",
        "data": {
            "id": incident.id,
            "status": stat_str,
            "phone_number": incident.phone_number,
            "emergency_type": incident.category.value if hasattr(incident.category, "value") else str(incident.category),
        },
    }
    await manager.broadcast_to_rooms(event, ["dashboard", "responders", "citizens"])

    return {"id": incident.id, "status": stat_str}
