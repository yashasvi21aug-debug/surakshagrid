from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.services.sitrep import sitrep_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/sitrep", response_model=dict[str, Any])
async def get_situation_report(
    hours: int = Query(default=12, ge=1, le=168),
    format: str = Query(default="json", description="json or pdf/markdown"),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Generate structured incident briefing data or formatted document for Incident Commanders (PRD Section 3 & 4.5)."""
    res = await sitrep_service.generate_sitrep(hours, format, db)
    if isinstance(res, dict):
        return res
    return {"markdown": res}
