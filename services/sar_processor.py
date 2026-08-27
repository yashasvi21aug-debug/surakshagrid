from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.gis_models import InundationZone


def otsu_threshold(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if values.size == 0:
        return 0.0
    hist, bin_edges = np.histogram(values, bins=256, range=(values.min(), values.max() or 1.0))
    hist = hist.astype(float)
    total = hist.sum()
    if total == 0:
        return 0.0

    sum_bg = 0.0
    w_bg = 0.0
    sum_total = np.dot(np.arange(len(hist)), hist)
    max_variance = 0.0
    threshold = 0.0

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
            threshold = t

    threshold_value = float(bin_edges[threshold])
    return threshold_value


def segment_water_mask(array: np.ndarray, threshold_db: float = -15.0) -> np.ndarray:
    if array.ndim == 3:
        band = array[0]
    else:
        band = array

    # Convert radar backscatter (linear power) to dB where lower values indicate water-like response.
    band_db = 10.0 * np.log10(np.clip(np.abs(band), 1e-8, None))
    mask = band_db < threshold_db
    return mask.astype(np.uint8)


def vectorize_water_mask(mask: np.ndarray, transform: Any, min_area: float = 100.0) -> gpd.GeoDataFrame:
    shapes_list = list(shapes(mask.astype("uint8"), mask=mask.astype("uint8"), transform=transform))
    geometries = []
    for geom, value in shapes_list:
        if value == 1 and geom is not None:
            polygon = shape(geom)
            if polygon.area >= min_area:
                geometries.append(polygon)

    if not geometries:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    merged = unary_union(geometries)
    if merged.geom_type == "MultiPolygon":
        polygons = list(merged.geoms)
    else:
        polygons = [merged]

    gdf = gpd.GeoDataFrame({"geometry": polygons}, geometry="geometry", crs="EPSG:4326")
    gdf = gdf[gdf.geometry.notnull()]
    gdf["geometry"] = gdf.geometry.simplify(0.0005, preserve_topology=True)
    return gdf


def process_sar_tif(input_path: str | Path, threshold_db: float = -15.0, min_area: float = 100.0) -> gpd.GeoDataFrame:
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"SAR file not found: {input_file}")

    with rasterio.open(input_file) as src:
        band_data = src.read()
        if band_data.ndim == 3 and band_data.shape[0] < 1:
            raise ValueError("No raster bands found in SAR file.")

        mask = segment_water_mask(band_data, threshold_db=threshold_db)
        gdf = vectorize_water_mask(mask, src.transform, min_area=min_area)

    if gdf.empty:
        return gdf

    if gdf.crs is None:
        gdf.set_crs(src.crs, inplace=True)

    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    gdf["zone_name"] = input_file.stem
    gdf["risk_score"] = 0.9
    gdf["estimated_water_rise"] = 1.5
    gdf["predicted_horizon_hours"] = 6
    return gdf


async def ingest_flood_polygons_to_db(gdf: gpd.GeoDataFrame) -> int:
    if gdf.empty:
        return 0

    async with AsyncSessionLocal() as session:
        count = 0
        for _, row in gdf.iterrows():
            polygon = row.geometry
            if polygon is None or polygon.is_empty:
                continue

            zone = InundationZone(
                zone_name=row.get("zone_name", "SAR_Inundation"),
                polygon=polygon.wkt,
                risk_score=float(row.get("risk_score", 0.9)),
                estimated_water_rise=float(row.get("estimated_water_rise", 1.5)),
                predicted_horizon_hours=int(row.get("predicted_horizon_hours", 6)),
            )
            session.add(zone)
            count += 1

        await session.commit()

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Process SAR flood inundation raster into PostGIS polygons")
    parser.add_argument("--input", required=True, help="Path to the SAR GeoTIFF input")
    parser.add_argument("--threshold-db", type=float, default=-15.0, help="Water segmentation threshold in dB")
    parser.add_argument("--min-area", type=float, default=100.0, help="Minimum polygon area for retaining a mask")
    args = parser.parse_args()

    gdf = process_sar_tif(args.input, threshold_db=args.threshold_db, min_area=args.min_area)
    print(f"Extracted {len(gdf)} polygon(s) from water mask.")

    import asyncio
    count = asyncio.run(ingest_flood_polygons_to_db(gdf))
    print(f"Persisted {count} inundation polygons into PostGIS.")


if __name__ == "__main__":
    main()
