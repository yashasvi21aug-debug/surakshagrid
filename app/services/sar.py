from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

WGS84 = "EPSG:4326"
AREA_CRS = "EPSG:6933"


@dataclass(frozen=True)
class SARProcessingResult:
    """Vector result and summary statistics from one Sentinel-1 SAR acquisition."""

    polygons: Any
    total_surface_water_area_sq_km: float
    source: str
    threshold_db: float


def _as_backscatter_db(values: np.ndarray) -> np.ndarray:
    """Return dB values, converting positive linear power values to decibels if required."""
    values = values.astype("float32", copy=False)
    finite = values[np.isfinite(values)]
    if finite.size and float(np.nanmin(finite)) >= 0.0:
        return (10.0 * np.log10(np.clip(values, 1e-8, None))).astype("float32")
    return values


def lee_speckle_filter(backscatter_db: np.ndarray, window_size: int = 7) -> np.ndarray:
    """Apply Lee speckle filter using scipy.ndimage local mean and variance calculation."""
    try:
        from scipy.ndimage import uniform_filter
    except ImportError:
        radius = window_size // 2
        padded = np.pad(backscatter_db, radius, mode="edge")
        windows = np.lib.stride_tricks.sliding_window_view(padded, (window_size, window_size))
        return np.nanmedian(windows, axis=(-2, -1)).astype("float32")

    raster_f = backscatter_db.astype(np.float32)
    mean = uniform_filter(raster_f, size=window_size)
    mean_sq = uniform_filter(raster_f**2, size=window_size)
    var = np.maximum(0.0, mean_sq - mean**2)

    overall_var = np.var(raster_f)
    if overall_var == 0:
        return raster_f

    weight = var / (var + overall_var)
    filtered = mean + weight * (raster_f - mean)
    return filtered.astype("float32")


def otsu_threshold(values: np.ndarray) -> float:
    """Calculate Otsu's optimal threshold for automatic water backscatter segmentation."""
    values = values[np.isfinite(values)]
    if values.size == 0:
        return -14.0
    hist, bin_edges = np.histogram(values, bins=256, range=(values.min(), values.max() or 1.0))
    hist = hist.astype(float)
    total = hist.sum()
    if total == 0:
        return -14.0

    sum_bg = 0.0
    w_bg = 0.0
    sum_total = np.dot(np.arange(len(hist)), hist)
    max_variance = 0.0
    threshold_idx = 0

    for t in range(len(hist)):
        w_bg += hist[t]
        if w_bg == 0:
            continue
        w_fg = total - w_bg
        if w_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / w_bg
        mean_fg = (sum_total - sum_bg) / w_fg
        variance_between = w_bg * w_fg * (mean_bg - mean_fg) ** 2
        if variance_between > max_variance:
            max_variance = variance_between
            threshold_idx = t

    cutoff = float(bin_edges[threshold_idx])
    return float(np.clip(cutoff, -22.0, -11.0))


def threshold_open_water(
    backscatter_db: np.ndarray,
    threshold_db: float | None = None,
    valid_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, float]:
    """Create a binary open-water mask from Sentinel-1 backscatter drops."""
    if threshold_db is None:
        computed_threshold = otsu_threshold(backscatter_db)
    else:
        computed_threshold = threshold_db

    mask = np.isfinite(backscatter_db) & (backscatter_db <= computed_threshold)
    if valid_mask is not None:
        mask &= valid_mask
    return mask.astype("uint8"), computed_threshold


def vectorize_water_mask(
    mask: np.ndarray,
    transform: Any,
    source_crs: Any = WGS84,
    smoothing_tolerance: float = 0.00015,
    min_polygon_area: float = 1e-6,
) -> Any:
    """Convert connected open-water pixels to smoothed GeoPandas WGS84 polygons."""
    try:
        from rasterio.features import shapes
    except ImportError:
        shapes = None

    geometries: list[Polygon] = []
    if shapes is not None and transform is not None:
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

    try:
        import geopandas as gpd
        gdf = gpd.GeoDataFrame({"geometry": geometries}, geometry="geometry", crs=source_crs or WGS84)
        return gdf.to_crs(WGS84)
    except ImportError:
        return geometries


def calculate_surface_water_area(polygons: Any) -> float:
    """Calculate surface water polygon area in square kilometres."""
    if hasattr(polygons, "empty") and polygons.empty:
        return 0.0
    if hasattr(polygons, "to_crs"):
        try:
            return round(float(polygons.to_crs(AREA_CRS).geometry.area.sum()) / 1_000_000, 4)
        except Exception:
            pass
    if isinstance(polygons, list):
        total_area = sum(p.area for p in polygons if hasattr(p, "area"))
        return round(float(total_area * 111.0 * 111.0), 4)
    return 0.0


def process_sar_tif(
    input_path: str | Path,
    threshold_db: float | None = None,
    speckle_window: int = 7,
    smoothing_tolerance: float = 0.00015,
) -> SARProcessingResult:
    """Process a Sentinel-1 GRD GeoTIFF raster into flood extent polygons."""
    input_file = Path(input_path)
    if not input_file.is_file():
        raise FileNotFoundError(f"SAR GeoTIFF not found: {input_file}")

    try:
        import rasterio
    except ImportError as err:
        raise RuntimeError("rasterio dependency is required for GeoTIFF processing") from err

    with rasterio.open(input_file) as source:
        if source.count < 1:
            raise ValueError("SAR input must contain at least one raster band")
        values = source.read(1, masked=True).filled(np.nan)
        valid_mask = ~np.ma.getmaskarray(source.read(1, masked=True))
        backscatter_db = _as_backscatter_db(values)
        filtered_db = lee_speckle_filter(backscatter_db, window_size=speckle_window)
        water_mask, used_threshold = threshold_open_water(filtered_db, threshold_db, valid_mask)
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
        threshold_db=used_threshold,
    )


def generate_mock_sar(
    width: int = 180,
    height: int = 140,
    west: float = 77.30,
    north: float = 28.76,
    pixel_size: float = 0.0015,
    seed: int = 3492,
) -> tuple[np.ndarray, Any, str]:
    """Generate a deterministic Sentinel-1 GRD dB SAR scene with synthetic flood bodies."""
    if width < 20 or height < 20:
        raise ValueError("Mock SAR dimensions must be at least 20 by 20 pixels")
    rng = np.random.default_rng(seed)
    scene = rng.normal(-8.5, 1.8, size=(height, width)).astype("float32")
    rows, columns = np.indices((height, width))
    first_water = ((columns - width * 0.35) / (width * 0.20)) ** 2 + ((rows - height * 0.48) / (height * 0.25)) ** 2 <= 1
    second_water = ((columns - width * 0.72) / (width * 0.14)) ** 2 + ((rows - height * 0.70) / (height * 0.18)) ** 2 <= 1
    scene[first_water | second_water] = rng.normal(-19.0, 1.4, size=(first_water | second_water).sum())

    try:
        from rasterio.transform import from_origin
        transform = from_origin(west, north, pixel_size, pixel_size)
    except ImportError:
        transform = None

    return scene, transform, WGS84


def generate_mock_sar_result() -> SARProcessingResult:
    """Run the pipeline against a synthetic Sentinel-1 scene when no raster TIFF is present."""
    scene, transform, crs = generate_mock_sar()
    filtered_db = lee_speckle_filter(scene)
    water_mask, used_threshold = threshold_open_water(filtered_db)
    polygons = vectorize_water_mask(water_mask, transform, crs)
    return SARProcessingResult(
        polygons=polygons,
        total_surface_water_area_sq_km=calculate_surface_water_area(polygons),
        source="synthetic-sentinel1-sar",
        threshold_db=used_threshold,
    )


def result_to_geojson(result: SARProcessingResult) -> dict[str, Any]:
    """Serialize a SAR processing result as a GeoJSON FeatureCollection."""
    if hasattr(result.polygons, "to_json"):
        feature_collection = result.polygons.to_json(drop_id=True)
        import json
        geojson = json.loads(feature_collection)
    else:
        features = []
        for poly in (result.polygons if isinstance(result.polygons, list) else []):
            features.append({
                "type": "Feature",
                "geometry": poly.__geo_interface__ if hasattr(poly, "__geo_interface__") else {"type": "Polygon", "coordinates": []},
                "properties": {"source": result.source},
            })
        geojson = {"type": "FeatureCollection", "features": features}

    for feature in geojson.get("features", []):
        feature.setdefault("properties", {})["source"] = result.source
    geojson["properties"] = {
        "source": result.source,
        "total_surface_water_area_sq_km": result.total_surface_water_area_sq_km,
        "threshold_db": result.threshold_db,
    }
    return geojson


async def ingest_flood_polygons_to_db(gdf: Any, db: Any | None = None) -> int:
    """Persist extracted SAR inundation polygons to PostGIS database."""
    if hasattr(gdf, "empty") and gdf.empty:
        return 0

    from app.models.spatial_models import FloodPolygon

    count = 0
    rows = gdf.iterrows() if hasattr(gdf, "iterrows") else enumerate(gdf if isinstance(gdf, list) else [])
    for _, row in rows:
        polygon = row.geometry if hasattr(row, "geometry") else row
        if polygon is None or getattr(polygon, "is_empty", True):
            continue

        zone_name = row.get("zone_name", "SAR_Sentinel1_Inundation") if hasattr(row, "get") else "SAR_Sentinel1_Inundation"
        depth_m = float(row.get("depth_m", 1.2)) if hasattr(row, "get") else 1.2
        risk_score = float(row.get("risk_score", 0.9)) if hasattr(row, "get") else 0.9

        zone = FloodPolygon(
            zone_name=zone_name,
            depth_m=depth_m,
            severity="HIGH",
            risk_score=risk_score,
            predicted_horizon_hours=6,
        )
        if db is not None:
            db.add(zone)
        count += 1

    if db is not None:
        await db.commit()

    return count
