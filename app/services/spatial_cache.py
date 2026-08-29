from __future__ import annotations

import logging
from typing import Any
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class SpatialCacheManager:
    """Thread-safe in-memory caching manager for spatial layers and GeoJSON geometries."""

    def __init__(self, maxsize: int = 256, ttl: float = 15.0) -> None:
        self._shelter_cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._flood_polygon_cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._sensor_cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)

    def get_shelters(self, key: str = "active_shelters") -> Any | None:
        """Get cached shelter geometries/features."""
        return self._shelter_cache.get(key)

    def set_shelters(self, data: Any, key: str = "active_shelters") -> None:
        """Cache shelter geometries/features."""
        self._shelter_cache[key] = data

    def get_flood_polygons(self, key: str = "active_flood_polygons") -> Any | None:
        """Get cached active flood polygons."""
        return self._flood_polygon_cache.get(key)

    def set_flood_polygons(self, data: Any, key: str = "active_flood_polygons") -> None:
        """Cache active flood polygons."""
        self._flood_polygon_cache[key] = data

    def get_sensors(self, key: str = "water_sensors") -> Any | None:
        """Get cached water sensors."""
        return self._sensor_cache.get(key)

    def set_sensors(self, data: Any, key: str = "water_sensors") -> None:
        """Cache water sensors."""
        self._sensor_cache[key] = data

    def invalidate_all(self) -> None:
        """Clear all spatial caches."""
        self._shelter_cache.clear()
        self._flood_polygon_cache.clear()
        self._sensor_cache.clear()
        logger.debug("Invalidated all spatial in-memory caches.")


spatial_cache = SpatialCacheManager()
