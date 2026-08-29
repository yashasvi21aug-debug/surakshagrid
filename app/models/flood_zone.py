from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.models.base import Base


class InundationZone(Base):
    __tablename__ = "inundation_zones"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_name = Column(String(100), unique=True, nullable=False, index=True)
    polygon = Column(String(4000), nullable=True)
    polygon_geojson = Column(String(4000), nullable=True)
    risk_score = Column(Float, nullable=False, default=0.5)
    water_depth_m = Column(Float, nullable=True, default=0.5)
    estimated_water_rise = Column(Float, nullable=False, default=0.5)
    predicted_horizon_hours = Column(Integer, nullable=False, default=6)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_geojson_geometry(self) -> dict[str, Any]:
        if self.polygon_geojson:
            try:
                return json.loads(self.polygon_geojson)
            except Exception:
                pass
        return {"type": "Polygon", "coordinates": []}

    def to_geojson_feature(self) -> dict[str, Any]:
        return {
            "type": "Feature",
            "geometry": self.to_geojson_geometry(),
            "properties": {
                "id": self.id,
                "zone_name": self.zone_name,
                "risk_score": self.risk_score,
                "water_depth_m": self.water_depth_m or self.estimated_water_rise,
                "estimated_water_rise": self.estimated_water_rise,
                "predicted_horizon_hours": self.predicted_horizon_hours,
                "created_at": self.created_at.isoformat() if hasattr(self.created_at, "isoformat") else str(self.created_at),
            },
        }


# Alias for backward compatibility
FloodZone = InundationZone
