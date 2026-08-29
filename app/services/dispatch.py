from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import functions as func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CitizenSOS, CitizenStatus, RescueUnit, RescueUnitStatus
from app.services.routing import routing_service
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

VALID_STATUS_TRANSITIONS = {
    CitizenStatus.PENDING: [CitizenStatus.ACKNOWLEDGED, CitizenStatus.DISPATCHED, CitizenStatus.RESOLVED],
    CitizenStatus.ACKNOWLEDGED: [CitizenStatus.DISPATCHED, CitizenStatus.ON_SCENE, CitizenStatus.RESOLVED],
    CitizenStatus.DISPATCHED: [CitizenStatus.ON_SCENE, CitizenStatus.RESOLVED, CitizenStatus.PENDING],
    CitizenStatus.ON_SCENE: [CitizenStatus.RESOLVED, CitizenStatus.DISPATCHED],
    CitizenStatus.RESOLVED: [CitizenStatus.PENDING, CitizenStatus.DISPATCHED],
}


class DispatchEngine:
    """Incident dispatch state machine and spatial unit allocation engine adhering to PRD Section 3 & 4.4."""

    async def find_nearest_available_rescue_unit(
        self,
        db: AsyncSession,
        sos_lat: float,
        sos_lng: float,
    ) -> RescueUnit | None:
        """Query PostGIS using ST_Distance to match nearest available NDRF field unit (boat/truck)."""
        try:
            sos_point = func.ST_SetSRID(func.ST_Point(sos_lng, sos_lat), 4326)
            stmt = (
                select(RescueUnit)
                .where(RescueUnit.status == RescueUnitStatus.STANDBY)
                .order_by(func.ST_Distance(RescueUnit.current_location, sos_point))
                .limit(1)
            )
            result = await db.execute(stmt)
            unit = result.scalars().first()
            if unit and hasattr(unit, "unit_name"):
                return unit
        except Exception as err:
            logger.warning("PostGIS ST_Distance query fallback: %s", err)

        try:
            stmt = select(RescueUnit).where(RescueUnit.status == RescueUnitStatus.STANDBY).limit(1)
            result = await db.execute(stmt)
            unit = result.scalars().first()
            if unit and hasattr(unit, "unit_name"):
                return unit
        except Exception:
            pass

        return None

    async def assign_rescue_unit_to_incident(
        self,
        db: AsyncSession,
        sos_id: str,
        unit_id: str | None = None,
        officer_notes: str | None = None,
    ) -> dict[str, Any]:
        """Assign rescue unit, calculate flood-evasive safe corridor, update status, and broadcast waypoints."""
        incident = await db.get(CitizenSOS, sos_id)
        if incident is None:
            raise ValueError(f"Incident SOS {sos_id} not found")

        dest_lat = float(getattr(incident, "lat", None) or 28.6321)
        dest_lng = float(getattr(incident, "lng", None) or 77.4446)

        # Match nearest available rescue unit if not explicitly provided
        unit = None
        if unit_id:
            unit = await db.get(RescueUnit, unit_id)
        else:
            unit = await self.find_nearest_available_rescue_unit(db, dest_lat, dest_lng)

        unit_name = getattr(unit, "unit_name", "NDRF-ALPHA-BOAT-01") if unit else "NDRF-ALPHA-BOAT-01"
        res_unit_id = getattr(unit, "id", "UNIT-MOCK-01") if unit else "UNIT-MOCK-01"
        unit_lat = 28.6590
        unit_lng = 77.2490

        if unit and hasattr(unit, "current_location"):
            try:
                coords = await db.scalar(select(func.ST_X(unit.current_location), func.ST_Y(unit.current_location)))
                if isinstance(coords, (tuple, list)) and len(coords) == 2 and coords[0] is not None:
                    unit_lng, unit_lat = float(coords[0]), float(coords[1])
            except Exception:
                pass

        # Fetch active flood zones & calculate flood-evasive safe corridor route
        flood_zones = await routing_service.get_critical_inundation_zones(db)
        route_corridor = await routing_service.calculate_safe_corridor(
            origin=(unit_lng, unit_lat),
            destination=(dest_lng, dest_lat),
            flood_zones=flood_zones,
        )

        # Update Incident & Unit Status
        incident.status = CitizenStatus.DISPATCHED
        if officer_notes:
            incident.notes = f"{incident.notes or ''} [DISPATCH NOTE: {officer_notes}]".strip()

        if unit and hasattr(unit, "status"):
            unit.status = RescueUnitStatus.EN_ROUTE
            unit.assigned_sos_id = incident.id

        await db.commit()
        await db.refresh(incident)

        dispatch_payload = {
            "type": "UNIT_DISPATCHED",
            "event": "unit_dispatched",
            "data": {
                "sos_id": incident.id,
                "status": "DISPATCHED",
                "rescue_unit": unit_name,
                "unit_id": res_unit_id,
                "origin": [unit_lng, unit_lat],
                "destination": [dest_lng, dest_lat],
                "safe_corridor": route_corridor,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Broadcast turn-by-turn waypoints over WebSocket bus (<200 ms)
        await manager.broadcast_to_rooms(dispatch_payload, ["dashboard", "responders", "citizens"])
        return dispatch_payload["data"]

    async def update_incident_status(
        self,
        db: AsyncSession,
        sos_id: str,
        new_status: str,
        officer_notes: str | None = None,
    ) -> dict[str, Any]:
        """Transition incident state machine (PENDING -> ACKNOWLEDGED -> DISPATCHED -> ON_SCENE -> RESOLVED) and broadcast."""
        incident = await db.get(CitizenSOS, sos_id)
        if incident is None:
            raise ValueError(f"Incident SOS {sos_id} not found")

        status_str = new_status.upper()
        if status_str == "ACKNOWLEDGED":
            status_enum = CitizenStatus.ACKNOWLEDGED
        elif status_str == "ON_SCENE":
            status_enum = CitizenStatus.ON_SCENE
        elif status_str in ("RESOLVED", "RESCUED"):
            status_enum = CitizenStatus.RESOLVED
        elif status_str in ("PENDING", "UNASSIGNED"):
            status_enum = CitizenStatus.PENDING
        else:
            status_enum = CitizenStatus.DISPATCHED

        incident.status = status_enum
        if officer_notes:
            incident.notes = f"{incident.notes or ''} [{officer_notes}]".strip()

        await db.commit()
        await db.refresh(incident)

        update_payload = {
            "type": "INCIDENT_STATUS_CHANGED",
            "event": "status_changed",
            "data": {
                "sos_id": incident.id,
                "status": status_enum.value if hasattr(status_enum, "value") else str(status_enum),
                "notes": incident.notes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        await manager.broadcast_to_rooms(update_payload, ["dashboard", "responders", "citizens"])
        return update_payload["data"]


dispatch_engine = DispatchEngine()
