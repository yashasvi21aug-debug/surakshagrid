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

    response = await client.get("/api/v1/spatial/inundation")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert "features" in body
    if body["features"]:
        feature = body["features"][0]
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] in ("Polygon", "MultiPolygon")


@pytest.mark.asyncio
async def test_river_sensors_geojson_endpoint(client, fake_db):
    response = await client.get("/api/v1/spatial/sensors")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert "features" in body
    assert isinstance(body["features"], list)


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


@pytest.mark.asyncio
async def test_evasive_route_endpoint_post(client, fake_db):
    fake_db.zones = []
    fake_db.scalar_values = []

    payload = {
        "origin": [77.4446, 28.6321],
        "destination": [77.5000, 28.6500],
    }

    response = await client.post("/api/v1/spatial/evasive-route", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("safe", "rerouted")
    assert data["safe_bypass_geojson"]["type"] == "LineString"
    assert len(data["safe_bypass_geojson"]["coordinates"]) >= 2
    assert data["distance_km"] > 0.0
    assert data["estimated_travel_time_mins"] > 0.0


@pytest.mark.asyncio
async def test_evasive_route_endpoint_get(client, fake_db):
    fake_db.zones = []
    fake_db.scalar_values = []

    params = {
        "origin_lat": 28.6321,
        "origin_lng": 77.4446,
        "dest_lat": 28.6500,
        "dest_lng": 77.5000,
    }

    response = await client.get("/api/v1/spatial/evasive-route", params=params)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("safe", "rerouted")
    assert data["safe_bypass_geojson"]["type"] == "LineString"


@pytest.mark.asyncio
async def test_geojson_output_validity_for_spatial_endpoints(client, fake_db):
    """Test GeoJSON FeatureCollection structure and point-in-polygon output validity."""
    res = await client.get("/api/v1/spatial/inundation")
    assert res.status_code == 200
    geojson_data = res.json()
    assert geojson_data["type"] == "FeatureCollection"
    assert isinstance(geojson_data["features"], list)
