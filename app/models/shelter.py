from __future__ import annotations

import enum
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, Integer, String, Text
from geoalchemy2 import Geometry

from app.database import Base


class ShelterStatus(str, enum.Enum):
    OPEN = "OPEN"
    FULL = "FULL"
    SUBMERGED = "SUBMERGED"


class Shelter(Base):
    __tablename__ = "shelters"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    lat = Column(Float, nullable=False, default=28.6590)
    lng = Column(Float, nullable=False, default=77.2490)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    max_capacity = Column(Integer, nullable=False, default=500)
    current_occupancy = Column(Integer, nullable=False, default=0)
    medical_support = Column(Boolean, nullable=False, default=True)
    food_supply_days = Column(Integer, nullable=False, default=7)
    status = Column(Enum(ShelterStatus), nullable=False, default=ShelterStatus.OPEN)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "max_capacity": self.max_capacity,
            "current_occupancy": self.current_occupancy,
            "available_slots": max(0, self.max_capacity - self.current_occupancy),
            "medical_support": self.medical_support,
            "food_supply_days": self.food_supply_days,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
        }
