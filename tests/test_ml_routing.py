from __future__ import annotations

import pytest

from app.services.routing_service import RoutingService


class StubPredictor:
    def predict_risk(self, lat: float, lng: float, rain_rate: float, discharge: float) -> dict:
        return {
            "lat": lat,
            "lng": lng,
            "risk_probability": 0.91,
            "water_rise_meters": 1.8,
            "should_flag_flood_polygon": True,
            "status": "HIGH",
        }


@pytest.mark.asyncio
async def test_evaluate_risk_endpoint(client, monkeypatch):
    import ml.predictor

    monkeypatch.setattr(ml.predictor, "_predictor", StubPredictor())
    response = await client.post(
        "/api/v1/ml/evaluate-risk",
        json={"lat": 28.63, "lng": 77.44, "rain_rate": 42, "discharge": 850},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "HIGH"
    assert response.json()["should_flag_flood_polygon"] is True


@pytest.mark.asyncio
async def test_evaluate_risk_rejects_incomplete_payload(client):
    response = await client.post(
        "/api/v1/ml/evaluate-risk",
        json={"lat": 28.63, "lng": 77.44},
    )

    assert response.status_code == 400
    assert "rain_rate" in response.json()["detail"]


@pytest.mark.asyncio
async def test_safe_dispatch_generates_detour_when_osrm_route_intersects_flood(
    fake_db, make_zone, monkeypatch
):
    service = RoutingService()
    fake_db.zones = [make_zone(risk_score=0.9)]
    fake_db.scalar_values = [True]

    async def fake_osrm_route(origin_coords, destination_coords, profile="driving"):
        return {
            "routes": [
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[77.44, 28.63], [77.46, 28.65]],
                    },
                    "legs": [{}],
                }
            ]
        }

    monkeypatch.setattr(service, "get_osrm_route", fake_osrm_route)
    result = await service.get_safe_dispatch_route(
        db=fake_db,
        origin_coords=(77.44, 28.63),
        destination_coords=(77.46, 28.65),
    )

    assert result["status"] == "rerouted"
    assert result["route_summary"] == {"detour": True, "source": "high_elevation_corridor"}
    assert result["route"]["coordinates"][0] == [77.44, 28.63]
    assert result["route"]["coordinates"][-1] == [77.46, 28.65]


def test_safe_detour_coordinates_preserve_origin_and_destination():
    service = RoutingService()

    coordinates = service.build_safe_detour_coordinates(
        origin_coords=(77.44, 28.63),
        destination_coords=(77.46, 28.65),
    )

    assert len(coordinates) == 5
    assert coordinates[0] == [77.44, 28.63]
    assert coordinates[-1] == [77.46, 28.65]
