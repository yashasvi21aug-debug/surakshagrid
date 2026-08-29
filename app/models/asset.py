from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String
from geoalchemy2 import Geometry

from app.database import Base


class AssetType(str, enum.Enum):
    INFLATABLE_BOAT = "INFLATABLE_BOAT"
    HIGH_AXLE_TRUCK = "HIGH_AXLE_TRUCK"
    AMPHIBIOUS_CRAFT = "AMPHIBIOUS_CRAFT"
    DRONE = "DRONE"


class AssetStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    DEPLOYED = "DEPLOYED"
    MAINTENANCE = "MAINTENANCE"


class RescueAsset(Base):
    __tablename__ = "rescue_assets"

    id = Column(String(64), primary_key=True, index=True)
    organization_name = Column(String(128), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False, default=AssetType.INFLATABLE_BOAT)
    capacity = Column(Integer, nullable=False, default=10)
    lat = Column(Float, nullable=False, default=28.6590)
    lng = Column(Float, nullable=False, default=77.2490)
    current_location = Column(Geometry("POINT", srid=4326), nullable=True)
    status = Column(Enum(AssetStatus), nullable=False, default=AssetStatus.AVAILABLE)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_name": self.organization_name,
            "asset_type": self.asset_type.value if hasattr(self.asset_type, "value") else str(self.asset_type),
            "capacity": self.capacity,
            "lat": self.lat,
            "lng": self.lng,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
        }
