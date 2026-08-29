from __future__ import annotations

import pytest

from app.models.incident import CitizenStatus


@pytest.mark.asyncio
async def test_submit_sos_returns_created_incident(client, fake_db):
    response = await client.post(
        "/api/v1/sos/",
        json={
            "phone": "+91 98765 43210",
            "emergencyType": "CRITICAL_TRAPPED",
            "lat": 28.6321,
            "lng": 77.4446,
            "rainRate": 31.5,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["phone_number"] == "+91 98765 43210"
    assert body["emergency_type"] == "CRITICAL_TRAPPED"
    assert body["lat"] == pytest.approx(28.6321)
    assert body["lng"] == pytest.approx(77.4446)
    assert body["status"] == "PENDING"
    assert len(fake_db.sos) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [("lat", 91), ("lat", -91), ("lng", 181), ("lng", -181)],
)
async def test_submit_sos_rejects_invalid_coordinates(client, field, value):
    payload = {
        "phone": "+919876543210",
        "emergencyType": "FOOD_WATER",
        "lat": 28.63,
        "lng": 77.44,
    }
    payload[field] = value

    response = await client.post("/api/v1/sos/", json=payload)

    assert response.status_code == 422
    assert any(error["loc"][-1] == field for error in response.json()["detail"])


@pytest.mark.asyncio
async def test_submit_sos_rejects_missing_phone(client):
    response = await client.post(
        "/api/v1/sos/",
        json={"emergencyType": "MEDICAL_EVAC", "lat": 28.63, "lng": 77.44},
    )

    assert response.status_code == 422
    assert any(error["loc"][-1] == "phone" for error in response.json()["detail"])


@pytest.mark.asyncio
async def test_update_sos_status(client, fake_db):
    create_response = await client.post(
        "/api/v1/sos/",
        json={
            "phone": "+919876543210",
            "emergencyType": "MEDICAL_EVAC",
            "lat": 28.63,
            "lng": 77.44,
        },
    )
    incident_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/sos/{incident_id}/status",
        json={"status": "DISPATCHED"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": incident_id, "status": "DISPATCHED"}
    assert fake_db.records[0].status == CitizenStatus.DISPATCHED


@pytest.mark.asyncio
async def test_acknowledge_sos_lifecycle(client, fake_db):
    create_response = await client.post(
        "/api/v1/sos/",
        json={
            "phone": "+919876543210",
            "emergencyType": "MEDICAL_EVAC",
            "lat": 28.63,
            "lng": 77.44,
        },
    )
    incident_id = create_response.json()["id"]

    response = await client.post(f"/api/v1/sos/{incident_id}/acknowledge")

    assert response.status_code == 200
    assert response.json()["status"] == "DISPATCHED"
    assert fake_db.records[0].status == CitizenStatus.DISPATCHED


@pytest.mark.asyncio
async def test_resolve_sos_lifecycle(client, fake_db):
    create_response = await client.post(
        "/api/v1/sos/",
        json={
            "phone": "+919876543210",
            "emergencyType": "CRITICAL_TRAPPED",
            "lat": 28.63,
            "lng": 77.44,
        },
    )
    incident_id = create_response.json()["id"]

    response = await client.post(f"/api/v1/sos/{incident_id}/resolve")

    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"
    assert fake_db.records[0].status == CitizenStatus.RESOLVED


@pytest.mark.asyncio
async def test_full_sos_incident_lifecycle(client, fake_db):
    """Integration flow: Creation -> Dispatch Acknowledgment -> Resolution."""
    # 1. Incident Creation
    create_res = await client.post(
        "/api/v1/sos/",
        json={
            "phone": "+919998887770",
            "emergencyType": "CRITICAL_TRAPPED",
            "lat": 28.6800,
            "lng": 77.3500,
            "rainRate": 45.0,
        },
    )
    assert create_res.status_code == 201
    inc_data = create_res.json()
    assert inc_data["status"] == "PENDING"
    inc_id = inc_data["id"]

    # 2. Status Progression (Acknowledge / Dispatch)
    ack_res = await client.post(f"/api/v1/sos/{inc_id}/acknowledge")
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "DISPATCHED"

    # 3. Incident Resolution
    res_res = await client.post(f"/api/v1/sos/{inc_id}/resolve")
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"
