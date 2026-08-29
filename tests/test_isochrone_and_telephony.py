from __future__ import annotations

import pytest
from app.services.isochrone import isochrone_service
from app.services.sms_gateway import sms_gateway_service


@pytest.mark.asyncio
async def test_isochrone_calculation():
    """Test 5, 10, 15-minute evacuation reachability isochrone generation."""
    res = await isochrone_service.calculate_isochrones(28.6590, 77.2490, "vehicle")
    assert res["type"] == "FeatureCollection"
    assert len(res["features"]) == 3
    assert res["features"][0]["properties"]["contour_minutes"] == 5


@pytest.mark.asyncio
async def test_sms_gateway_inbound_parsing(fake_db):
    """Test SMS parsing, PostGIS persistence, and confirmation message dispatch."""
    body = "SOS CRITICAL 28.5355 77.3910 4 family members trapped on rooftop"
    res = await sms_gateway_service.parse_and_process_inbound_sms("+91-9876543210", body, fake_db)
    assert res["status"] == "SUCCESS"
    assert res["category"] == "CRITICAL_TRAPPED"
    assert res["coordinates"]["lat"] == 28.5355
    assert "SurakshaGrid Alert Code" in res["confirmation_sms"]
