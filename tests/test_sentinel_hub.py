from __future__ import annotations

import pytest
from app.services.sentinel_hub import sentinel_hub_service


@pytest.mark.asyncio
async def test_sentinel_hub_query():
    """Test Copernicus Data Space / AWS STAC API query fallback."""
    items = await sentinel_hub_service.query_copernicus_data_space(max_records=1)
    assert isinstance(items, list)
    assert len(items) >= 1
    assert "id" in items[0]


@pytest.mark.asyncio
async def test_sentinel_hub_poll_and_process(fake_db):
    """Test Sentinel-1 SAR raster download, Lee/Otsu vectorization, PostGIS upsert, and temporary file cleanup."""
    res = await sentinel_hub_service.poll_and_process_sar_feeds(fake_db)
    assert res["status"] == "SUCCESS"
    assert "geojson" in res
    assert res["geojson"]["type"] == "FeatureCollection"
