from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_assign_rescue_unit_endpoint(client):
    """Test POST /api/v1/dispatch/assign endpoint."""
    # First submit an SOS incident
    sos_res = await client.post(
        "/api/v1/sos/",
        json={
            "phone": "+91-9988776655",
            "emergencyType": "CRITICAL_TRAPPED",
            "lat": 28.6321,
            "lng": 77.4446,
            "notes": "Trapped family test dispatch",
        },
    )
    assert sos_res.status_code == 201
    sos_id = sos_res.json()["id"]

    # Assign rescue unit
    assign_res = await client.post(
        "/api/v1/dispatch/assign",
        json={
            "sos_id": sos_id,
            "officer_notes": "Dispatching NDRF Alpha Boat 01",
        },
    )
    assert assign_res.status_code == 200
    data = assign_res.json()
    assert data["sos_id"] == sos_id
    assert data["status"] == "DISPATCHED"
    assert "safe_corridor" in data


@pytest.mark.asyncio
async def test_update_dispatch_status_endpoint(client):
    """Test PATCH /api/v1/dispatch/incident/{id}/status endpoint."""
    sos_res = await client.post(
        "/api/v1/sos/",
        json={
            "phone": "+91-9988776655",
            "emergencyType": "MEDICAL_EVAC",
            "lat": 28.6321,
            "lng": 77.4446,
        },
    )
    sos_id = sos_res.json()["id"]

    patch_res = await client.patch(
        f"/api/v1/dispatch/incident/{sos_id}/status",
        json={"status": "RESOLVED", "officer_notes": "Evacuation complete"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "RESOLVED"
