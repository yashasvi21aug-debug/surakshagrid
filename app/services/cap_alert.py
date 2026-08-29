from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from xml.dom import minidom

logger = logging.getLogger(__name__)


class CAPAlertService:
    """Common Alerting Protocol (OASIS CAP v1.2) XML & RSS feed generation service (PRD Section 1 & 4.2)."""

    def generate_cap_xml(
        self,
        alert_id: str = "SURAKSHAGRID-ALERT-2026-001",
        event_name: str = "Urban Severe Inundation Flash Flood",
        polygon_coords: str = "28.6300,77.4400 28.6300,77.4550 28.6420,77.4550 28.6420,77.4400 28.6300,77.4400",
    ) -> str:
        """Convert active FloodZone polygons and river sensor alerts into standard OASIS CAP v1.2 XML format."""
        alert = ET.Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")

        ET.SubElement(alert, "identifier").text = alert_id
        ET.SubElement(alert, "sender").text = "eoc@surakshagrid.gov.in"
        ET.SubElement(alert, "sent").text = datetime.now(timezone.utc).isoformat()
        ET.SubElement(alert, "status").text = "Actual"
        ET.SubElement(alert, "msgType").text = "Alert"
        ET.SubElement(alert, "scope").text = "Public"

        info = ET.SubElement(alert, "info")
        ET.SubElement(info, "category").text = "Met"
        ET.SubElement(info, "event").text = event_name
        ET.SubElement(info, "urgency").text = "Immediate"
        ET.SubElement(info, "severity").text = "Extreme"
        ET.SubElement(info, "certainty").text = "Observed"
        ET.SubElement(info, "headline").text = "MANDATORY EVACUATION: Hindon River Basin Flash Flood Warning"
        ET.SubElement(info, "description").text = "Rapid water level rise detected by river sensors and Sentinel-1 SAR radar. Move to designated high-ground shelters."

        area = ET.SubElement(info, "area")
        ET.SubElement(area, "areaDesc").text = "Hindon & Yamuna Sub-Catchment Inundation Zone"
        ET.SubElement(area, "polygon").text = polygon_coords

        raw_str = ET.tostring(alert, encoding="utf-8")
        parsed = minidom.parseString(raw_str)
        return parsed.toprettyxml(indent="  ")

    def generate_rss_atom_feed(self) -> str:
        """Generate Atom/RSS syndication feed for public safety networks."""
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "SurakshaGrid National Emergency Alerts"
        ET.SubElement(channel, "link").text = "https://surakshagrid.gov.in"
        ET.SubElement(channel, "description").text = "Real-time AI Flood Emergency Feed"

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "CRITICAL FLOOD ALERT: Hindon Barrage Breach"
        ET.SubElement(item, "link").text = "https://surakshagrid.gov.in/alerts/001"
        ET.SubElement(item, "pubDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        ET.SubElement(item, "guid").text = "SURAKSHAGRID-RSS-001"

        raw_str = ET.tostring(rss, encoding="utf-8")
        parsed = minidom.parseString(raw_str)
        return parsed.toprettyxml(indent="  ")


cap_alert_service = CAPAlertService()
