from __future__ import annotations

import logging
from fastapi import APIRouter, Response, status

from app.services.cap_alert import cap_alert_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("/cap.xml")
async def get_cap_xml_alerts():
    """Return active emergency alert collection in standard OASIS CAP v1.2 XML format (PRD Section 1 & 4.2)."""
    xml_content = cap_alert_service.generate_cap_xml()
    return Response(content=xml_content, media_type="application/xml")


@router.get("/rss")
async def get_rss_alerts():
    """Return Atom/RSS feed for syndication with external public safety networks."""
    rss_content = cap_alert_service.generate_rss_atom_feed()
    return Response(content=rss_content, media_type="application/rss+xml")
