from __future__ import annotations

from fastapi import APIRouter, Depends

from app.routes.auth import OfficerPrincipal, require_role

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.post("/geofence")
async def create_geofence_alert(
    payload: dict,
    officer: OfficerPrincipal = Depends(require_role("COMMANDER")),
) -> dict:
    """Accept a command geofence definition after COMMANDER authorization."""
    return {
        "status": "accepted",
        "alert": payload,
        "created_by": officer.badge_id,
    }
