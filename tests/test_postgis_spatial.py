import pytest
from app.services.spatial import postgis_service


@pytest.mark.asyncio
async def test_postgis_point_in_polygon_fallback(fake_db):
    result = await postgis_service.check_point_in_polygon(28.6270, 77.2190, fake_db)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_postgis_route_intersection_fallback(fake_db):
    coords = [(77.2190, 28.6270), (77.2340, 28.6380), (77.2485, 28.6550)]
    result = await postgis_service.check_route_intersection(coords, fake_db)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_postgis_gauge_buffers_fallback(fake_db):
    result = await postgis_service.calculate_river_gauge_buffers(500.0, fake_db)
    assert isinstance(result, list)
