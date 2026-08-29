from __future__ import annotations

import random
import pytest

from app.main import app


def test_openapi_schema_generation():
    """Verify that OpenAPI v3 specification generates cleanly without schema errors."""
    schema = app.openapi()
    assert schema["openapi"].startswith("3.")
    assert "/api/v1/sos/" in schema["paths"]
    assert "/api/v1/routes/safe-corridor" in schema["paths"]
    assert "/api/v1/spatial/inundation" in schema["paths"]


@pytest.mark.asyncio
@pytest.mark.parametrize("run", range(15))
async def test_property_fuzz_sos_endpoint(client, run: int):
    """Property-based fuzz testing for POST /api/v1/sos/ endpoint."""
    categories = ["CRITICAL_TRAPPED", "MEDICAL_EVAC", "FOOD_WATER", "INVALID_CAT", ""]
    lat_options = [28.6321, 91.0, -91.0, 500.0, -500.0, 0.0]
    lng_options = [77.4446, 181.0, -181.0, 500.0, -500.0, 0.0]

    lat = random.choice(lat_options)
    lng = random.choice(lng_options)
    category = random.choice(categories)

    payload = {
        "phone": f"+91-98{random.randint(10000000, 99999999)}",
        "emergencyType": category,
        "category": category,
        "lat": lat,
        "lng": lng,
    }

    response = await client.post("/api/v1/sos/", json=payload)
    # The server MUST respond with either 201 (Valid), 422 (Validation Error), or 400 (Bad Request).
    # It MUST NEVER crash with an unhandled 500 Internal Server Error.
    assert response.status_code in (201, 400, 422), f"Unhandled server crash HTTP {response.status_code}: {response.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize("run", range(10))
async def test_property_fuzz_routing_endpoint(client, run: int):
    """Property-based fuzz testing for POST /api/v1/routes/safe-corridor endpoint."""
    start_lat = random.uniform(-200.0, 200.0)
    start_lng = random.uniform(-200.0, 200.0)
    end_lat = random.uniform(-200.0, 200.0)
    end_lng = random.uniform(-200.0, 200.0)

    payload = {
        "start_lat": start_lat,
        "start_lng": start_lng,
        "end_lat": end_lat,
        "end_lng": end_lng,
        "vehicle_type": "driving",
    }

    response = await client.post("/api/v1/routes/safe-corridor", json=payload)
    assert response.status_code in (200, 400, 422), f"Unhandled server crash HTTP {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_contract_malformed_json_payloads(client):
    """Contract verification for malformed or truncated JSON payloads."""
    malformed_bodies = [
        "{ invalid json",
        '{"category": "CRITICAL_TRAPPED", "lat": }',
        '{"lat": "NOT_A_NUMBER"}',
        "[]",
        "12345",
    ]

    for body in malformed_bodies:
        response = await client.post(
            "/api/v1/sos/",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (400, 422)
        assert response.headers["Content-Type"].startswith("application/")
