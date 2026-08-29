from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.routes.auth import require_role
from app.services.dispatch import dispatch_engine

router = APIRouter(prefix="/api/v1/dispatch", tags=["Dispatch Engine"])


class DispatchAssignRequest(BaseModel):
    sos_id: str
    unit_id: Optional[str] = None
    officer_notes: Optional[str] = None


class DispatchStatusUpdateRequest(BaseModel):
    status: str
    officer_notes: Optional[str] = None


@router.post("/assign", response_model=dict[str, Any])
async def assign_rescue_unit(
    payload: DispatchAssignRequest,
    db: AsyncSession = Depends(get_async_db),
    officer: Any = Depends(require_role("COMMANDER", "FIELD_OPERATOR")),
) -> dict[str, Any]:
    """Assign rescue team to active SOS incident, calculate flood-evasive safe corridor, and broadcast waypoints."""
    try:
        result = await dispatch_engine.assign_rescue_unit_to_incident(
            db=db,
            sos_id=payload.sos_id,
            unit_id=payload.unit_id,
            officer_notes=payload.officer_notes,
        )
        return result
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@router.patch("/incident/{id}/status", response_model=dict[str, Any])
async def update_dispatch_status(
    id: str,
    payload: DispatchStatusUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    officer: Any = Depends(require_role("COMMANDER", "FIELD_OPERATOR")),
) -> dict[str, Any]:
    """Update incident dispatch state machine and broadcast update over WebSockets."""
    try:
        result = await dispatch_engine.update_incident_status(
            db=db,
            sos_id=id,
            new_status=payload.status,
            officer_notes=payload.officer_notes,
        )
        return result
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
