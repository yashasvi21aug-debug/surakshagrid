import os
import tempfile
import numpy as np
import pytest

from app.services.sar import (
    SARProcessingResult,
    generate_mock_sar,
    generate_mock_sar_result,
    ingest_flood_polygons_to_db,
    lee_speckle_filter,
    otsu_threshold,
    process_sar_tif,
    result_to_geojson,
    threshold_open_water,
)


@pytest.fixture
def sample_sar_scene():
    scene, transform, crs = generate_mock_sar(width=100, height=80, seed=42)
    return scene, transform, crs


def test_lee_speckle_filter(sample_sar_scene):
    scene, _, _ = sample_sar_scene
    filtered = lee_speckle_filter(scene, window_size=5)
    assert filtered.shape == scene.shape
    assert filtered.dtype == np.float32


def test_otsu_threshold(sample_sar_scene):
    scene, _, _ = sample_sar_scene
    threshold = otsu_threshold(scene)
    assert isinstance(threshold, float)
    assert -25.0 <= threshold <= 0.0


def test_threshold_open_water(sample_sar_scene):
    scene, _, _ = sample_sar_scene
    mask, threshold = threshold_open_water(scene)
    assert mask.shape == scene.shape
    assert mask.dtype == np.uint8
    assert set(np.unique(mask)).issubset({0, 1})


def test_generate_mock_sar_result():
    result = generate_mock_sar_result()
    assert isinstance(result, SARProcessingResult)
    assert result.total_surface_water_area_sq_km >= 0.0
    assert result.source == "synthetic-sentinel1-sar"

    geojson = result_to_geojson(result)
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert "properties" in geojson
    assert geojson["properties"]["total_surface_water_area_sq_km"] == result.total_surface_water_area_sq_km


@pytest.mark.asyncio
async def test_ingest_flood_polygons_to_db(fake_db):
    result = generate_mock_sar_result()
    count = await ingest_flood_polygons_to_db(result.polygons, db=fake_db)
    assert isinstance(count, int)


def test_process_sar_tif_with_geotiff(sample_sar_scene):
    scene, transform, crs = sample_sar_scene
    try:
        import rasterio
    except ImportError:
        pytest.skip("rasterio not available")

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with rasterio.open(
            tmp_path,
            "w",
            driver="GTiff",
            height=scene.shape[0],
            width=scene.shape[1],
            count=1,
            dtype=scene.dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(scene, 1)

        result = process_sar_tif(tmp_path)
        assert isinstance(result, SARProcessingResult)
        assert result.source == tmp_path
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.mark.asyncio
async def test_sar_ingest_api_endpoint(client):
    """Test POST /api/v1/spatial/sar-ingest REST endpoint."""
    response = await client.post(
        "/api/v1/spatial/sar-ingest",
        params={"s3_uri": "s3://sentinel-1-bucket/GRD/2026/08/29/scene1.tif"},
    )
    assert response.status_code == 200
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert len(geojson["features"]) >= 1
    assert geojson["features"][0]["geometry"]["type"] == "Polygon"
