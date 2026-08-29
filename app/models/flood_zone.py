from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FloodZone(Base):
    __tablename__ = "flood_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="SAR")
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="HIGH")
    depth_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    polygon: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Backward compatibility attributes & properties
    zone_name: Mapped[str | None] = mapped_column(String(128), nullable=True, default="Inundation Zone")
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    estimated_water_rise: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    predicted_horizon_hours: Mapped[int] = mapped_column(Float, nullable=False, default=6)
    polygon_geojson: Mapped[str | None] = mapped_column(String(4000), nullable=True)

    @property
    def water_depth_m(self) -> float:
        return self.depth_m

    @water_depth_m.setter
    def water_depth_m(self, value: float) -> None:
        self.depth_m = value

    @property
    def geom(self) -> Any:
        return self.polygon

    @geom.setter
    def geom(self, value: Any) -> None:
        self.polygon = value

    @property
    def severity(self) -> str:
        return self.risk_level

    @severity.setter
    def severity(self, value: str) -> None:
        self.risk_level = value

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
                "source": self.source,
                "risk_level": self.risk_level,
                "depth_m": self.depth_m,
                "valid_until": self.valid_until.isoformat() if self.valid_until else None,
                "zone_name": self.zone_name or "Inundation Zone",
                "risk_score": self.risk_score,
                "created_at": self.created_at.isoformat() if hasattr(self.created_at, "isoformat") else str(self.created_at),
            },
        }


# Aliases for backward compatibility
InundationZone = FloodZone
FloodPolygon = FloodZone
