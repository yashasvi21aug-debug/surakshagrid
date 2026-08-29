from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Enum, Float, String

from app.models.base import Base


class EmergencyType(str, enum.Enum):
    CRITICAL_TRAPPED = "CRITICAL_TRAPPED"
    MEDICAL_EVAC = "MEDICAL_EVAC"
    FOOD_WATER = "FOOD_WATER"
    INFRASTRUCTURE_DAMAGE = "INFRASTRUCTURE_DAMAGE"


class CitizenStatus(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    RESCUED = "RESCUED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class CitizenSOS(Base):
    __tablename__ = "citizen_sos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(20), nullable=False, index=True)
    emergency_type = Column(Enum(EmergencyType), nullable=False)
    location = Column(String(255), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    rain_rate = Column(Float, nullable=True)
    risk_status = Column(String(20), default="LOW", nullable=False)
    status = Column(Enum(CitizenStatus), default=CitizenStatus.PENDING, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_geojson_feature(self) -> dict[str, Any]:
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.lng or 0.0, self.lat or 0.0],
            },
            "properties": {
                "id": self.id,
                "phone_number": self.phone_number,
                "emergency_type": self.emergency_type.value if hasattr(self.emergency_type, "value") else str(self.emergency_type),
                "status": self.status.value if hasattr(self.status, "value") else str(self.status),
                "risk_status": self.risk_status,
                "rain_rate": self.rain_rate,
                "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
            },
        }


# Alias for backward compatibility
SOSIncident = CitizenSOS
