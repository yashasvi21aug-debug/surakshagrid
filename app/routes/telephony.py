from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.services.sms_gateway import sms_gateway_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/telephony", tags=["telephony"])


@router.post("/sms-webhook", response_model=dict[str, Any])
async def handle_inbound_sms_webhook(
    From: str = Form(default="+91-9876543210"),
    Body: str = Form(default="SOS CRITICAL 28.5355 77.3910 Family trapped near flood dike"),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Inbound SMS Webhook for citizens without internet or data connectivity (PRD Section 4.1)."""
    return await sms_gateway_service.parse_and_process_inbound_sms(From, Body, db)
