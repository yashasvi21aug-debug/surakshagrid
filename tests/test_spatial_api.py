from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_inundation_zones_serialize_postgis_geojson_string(client, fake_db, make_zone):
    fake_db.zones = [make_zone()]
    fake_db.scalar_values = [
        json.dumps(
            {
                "type": "Polygon",
                "coordinates": [[[77.4, 28.6], [77.5, 28.6], [77.5, 28.7], [77.4, 28.6]]],
            }
        )
    ]

    response = await client.get("/api/v1/spatial/inundation-zones")

    assert response.status_code == 200
    feature = response.json()["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["zone_name"] == "Yamuna Critical Sector"
    assert feature["properties"]["risk_score"] == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_nearby_sos_returns_coordinates_and_distance(client, fake_db, make_incident):
    incident = make_incident()
    fake_db.sos = [incident]
    fake_db.scalar_values = [(77.4446, 28.6321), 143.75]

    response = await client.get(
        "/api/v1/spatial/nearby-sos",
        params={"lat": 28.63, "lng": 77.44, "radius_km": 5},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == incident.id
    assert item["lat"] == pytest.approx(28.6321)
    assert item["lng"] == pytest.approx(77.4446)
    assert item["distance_m"] == pytest.approx(143.75)
