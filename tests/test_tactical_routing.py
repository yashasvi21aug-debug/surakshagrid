import pytest
from shapely.geometry import Polygon

from app.schemas import EvasiveRouteRequest
from app.services.routing import ActiveFloodZone, RoutingService, routing_service


@pytest.fixture
def mock_flood_zone():
    # Polygon around (77.35, 28.65)
    poly = Polygon([
        (77.34, 28.64),
        (77.36, 28.64),
        (77.36, 28.66),
        (77.34, 28.66),
        (77.34, 28.64),
    ])
    return {
        "water_depth_m": 1.2,
        "coordinates": list(poly.exterior.coords),
    }


@pytest.mark.asyncio
async def test_fetch_osrm_route_fallback():
    service = RoutingService(osrm_base_url="http://invalid-osrm-host:9999")
    route_data = await service.fetch_osrm_route(
        origin=(77.30, 28.70),
        destination=(77.40, 28.70),
    )
    assert route_data["code"] == "Ok"
    assert "routes" in route_data
    assert len(route_data["routes"][0]["geometry"]["coordinates"]) >= 2


@pytest.mark.asyncio
async def test_calculate_safe_corridor_unblocked():
    corridor = await routing_service.calculate_safe_corridor(
        origin=(77.30, 28.70),
        destination=(77.31, 28.71),
        flood_zones=[],
    )
    assert corridor["status"] == "safe"
    assert corridor["passability"] == "CLEAR"
    assert "safe_bypass_geojson" in corridor
    assert corridor["distance_km"] >= 0.0
    assert corridor["estimated_travel_time_mins"] >= 0.0
    assert len(corridor["steps"]) >= 1


@pytest.mark.asyncio
async def test_calculate_safe_corridor_hazard_avoidance(mock_flood_zone):
    # Route right through the flood polygon
    corridor = await routing_service.calculate_safe_corridor(
        origin=(77.30, 28.65),
        destination=(77.40, 28.65),
        flood_zones=[mock_flood_zone],
    )
    assert corridor["status"] == "rerouted"
    assert corridor["passability"] == "REROUTED_SAFE"
    assert corridor["intersections_avoided"] == 1
    assert "HAZARD_BYPASS_ENGAGED" in corridor["safety_flags"]
    assert len(corridor["steps"]) >= 1


@pytest.mark.asyncio
async def test_evasive_route_api_endpoint(client):
    payload = {
        "origin": [77.30, 28.70],
        "destination": [77.40, 28.70],
        "avoid_water_depth_m": 0.3,
    }
    response = await client.post("/api/v1/spatial/evasive-route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "safe_bypass_geojson" in data
    assert "distance_km" in data
    assert "estimated_travel_time_mins" in data
