from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.services.post_mortem import post_mortem_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/archive", tags=["archive"])


@router.get("/export-spatial", response_model=dict[str, Any])
async def export_spatial_audit_archive(
    event_id: str = Query(default="EVENT-HINDON-FLOOD-2026"),
    format: str = Query(default="geojson", description="geojson, geopackage, shapefile"),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Export historical maximum flood inundation extents and incident lifecycle audit logs (PRD Section 4.2 & 5)."""
    return await post_mortem_service.export_spatial_archive(event_id, format, db)
