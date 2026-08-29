from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.services.dam_telemetry import dam_telemetry_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/hydrology", tags=["hydrology"])


@router.post("/dam-discharge", response_model=dict[str, Any])
async def ingest_dam_discharge(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Ingest upstream dam water release rates and simulate downstream surge wave front (PRD Section 4.3)."""
    dam_name = payload.get("dam_name", "Hindon Barrage Gate 01")
    discharge = float(payload.get("discharge_m3_s", 2400.0))
    lead_time = float(payload.get("lead_time_hours", 6.0))

    return await dam_telemetry_service.ingest_discharge_and_predict_surge(
        dam_name, discharge, lead_time
    )
