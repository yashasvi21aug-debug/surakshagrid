from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from affine import Affine
from rasterio.features import shapes
from rasterio.transform import from_origin
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union


WGS84 = "EPSG:4326"
AREA_CRS = "EPSG:6933"


@dataclass(frozen=True)
class SARProcessingResult:
    """Vector result and summary statistics from one SAR acquisition."""

    polygons: gpd.GeoDataFrame
    total_surface_water_area_sq_km: float
    source: str


def _as_backscatter_db(values: np.ndarray) -> np.ndarray:
    """Return dB values, accepting either dB rasters or positive linear power."""
    values = values.astype("float32", copy=False)
    finite = values[np.isfinite(values)]
    if finite.size and float(np.nanmin(finite)) >= 0.0:
        return (10.0 * np.log10(np.clip(values, 1e-8, None))).astype("float32")
    return values


def reduce_speckle(backscatter_db: np.ndarray, window_size: int = 3) -> np.ndarray:
    """Apply a local median filter that preserves water/land edges."""
    if window_size < 3 or window_size % 2 == 0:
        raise ValueError("window_size must be an odd integer greater than or equal to 3")
    radius = window_size // 2
    padded = np.pad(backscatter_db, radius, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (window_size, window_size))
    return np.nanmedian(windows, axis=(-2, -1)).astype("float32")


def threshold_open_water(
    backscatter_db: np.ndarray,
    threshold_db: float = -14.0,
    valid_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Create a binary open-water mask from low Sentinel-1 backscatter pixels."""
    mask = np.isfinite(backscatter_db) & (backscatter_db <= threshold_db)
    if valid_mask is not None:
        mask &= valid_mask
    return mask.astype("uint8")


def vectorize_water_mask(
    mask: np.ndarray,
    transform: Affine,
    source_crs: Any = WGS84,
    smoothing_tolerance: float = 0.00015,
    min_polygon_area: float = 0.0,
) -> gpd.GeoDataFrame:
    """Convert connected water pixels to smoothed WGS84 polygons."""
    geometries: list[Polygon] = []
    for geometry, value in shapes(mask.astype("uint8"), mask=mask.astype(bool), transform=transform):
        if value != 1:
            continue
        polygon = shape(geometry)
        if polygon.is_empty or polygon.area < min_polygon_area:
            continue
        if smoothing_tolerance > 0:
            polygon = polygon.buffer(smoothing_tolerance).buffer(-smoothing_tolerance)
        polygon = polygon.simplify(smoothing_tolerance, preserve_topology=True)
        if not polygon.is_empty and polygon.is_valid:
            geometries.append(polygon)

    if geometries:
        merged = unary_union(geometries)
        if merged.geom_type == "Polygon":
            geometries = [merged]
        elif merged.geom_type == "MultiPolygon":
            geometries = list(merged.geoms)
        else:
            geometries = []

    return gpd.GeoDataFrame({"geometry": geometries}, geometry="geometry", crs=source_crs or WGS84).to_crs(WGS84)


def calculate_surface_water_area(polygons: gpd.GeoDataFrame) -> float:
    """Calculate polygon area in square kilometres using a metric equal-area CRS."""
    if polygons.empty:
        return 0.0
    return round(float(polygons.to_crs(AREA_CRS).geometry.area.sum()) / 1_000_000, 4)


def process_sar_tif(
    input_path: str | Path,
    threshold_db: float = -14.0,
    speckle_window: int = 3,
    smoothing_tolerance: float = 0.00015,
) -> SARProcessingResult:
    """Process a single-band Sentinel-1 GRD GeoTIFF into flood polygons."""
    input_file = Path(input_path)
    if not input_file.is_file():
        raise FileNotFoundError(f"SAR GeoTIFF not found: {input_file}")

    with rasterio.open(input_file) as source:
        if source.count != 1:
            raise ValueError("SAR input must contain exactly one raster band")
        values = source.read(1, masked=True).filled(np.nan)
        valid_mask = ~np.ma.getmaskarray(source.read(1, masked=True))
        backscatter_db = _as_backscatter_db(values)
        filtered_db = reduce_speckle(backscatter_db, window_size=speckle_window)
        water_mask = threshold_open_water(filtered_db, threshold_db, valid_mask)
        polygons = vectorize_water_mask(
            water_mask,
            source.transform,
            source.crs or WGS84,
            smoothing_tolerance=smoothing_tolerance,
        )

    return SARProcessingResult(
        polygons=polygons,
        total_surface_water_area_sq_km=calculate_surface_water_area(polygons),
        source=str(input_file),
    )


def generate_mock_sar(
    width: int = 180,
    height: int = 140,
    west: float = 77.30,
    north: float = 28.76,
    pixel_size: float = 0.0015,
    seed: int = 3492,
) -> tuple[np.ndarray, Affine, str]:
    """Generate a deterministic dB SAR scene with two synthetic water bodies."""
    if width < 20 or height < 20:
        raise ValueError("Mock SAR dimensions must be at least 20 by 20 pixels")
    rng = np.random.default_rng(seed)
    scene = rng.normal(-8.5, 1.8, size=(height, width)).astype("float32")
    rows, columns = np.indices((height, width))
    first_water = ((columns - width * 0.35) / (width * 0.20)) ** 2 + ((rows - height * 0.48) / (height * 0.25)) ** 2 <= 1
    second_water = ((columns - width * 0.72) / (width * 0.14)) ** 2 + ((rows - height * 0.70) / (height * 0.18)) ** 2 <= 1
    scene[first_water | second_water] = rng.normal(-19.0, 1.4, size=(first_water | second_water).sum())
    return scene, from_origin(west, north, pixel_size, pixel_size), WGS84


def generate_mock_sar_result() -> SARProcessingResult:
    """Run the complete pipeline against the synthetic scene when no TIFF is available."""
    scene, transform, crs = generate_mock_sar()
    filtered_db = reduce_speckle(scene)
    water_mask = threshold_open_water(filtered_db)
    polygons = vectorize_water_mask(water_mask, transform, crs)
    return SARProcessingResult(
        polygons=polygons,
        total_surface_water_area_sq_km=calculate_surface_water_area(polygons),
        source="synthetic-demo-sar",
    )


def result_to_geojson(result: SARProcessingResult) -> dict[str, Any]:
    """Serialize a processing result as a dashboard-ready GeoJSON FeatureCollection."""
    feature_collection = result.polygons.to_json(drop_id=True)
    import json

    geojson = json.loads(feature_collection)
    for feature in geojson["features"]:
        feature.setdefault("properties", {})["source"] = result.source
    geojson["properties"] = {
        "source": result.source,
        "total_surface_water_area_sq_km": result.total_surface_water_area_sq_km,
        "threshold_db": -14.0,
    }
    return geojson
