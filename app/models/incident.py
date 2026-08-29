from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IncidentCategory(str, enum.Enum):
    CRITICAL_TRAPPED = "CRITICAL_TRAPPED"
    MEDICAL_EVAC = "MEDICAL_EVAC"
    FOOD_WATER = "FOOD_WATER"
    INFRASTRUCTURE_DAMAGE = "INFRASTRUCTURE_DAMAGE"


class IncidentStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISPATCHED = "DISPATCHED"
    ON_SCENE = "ON_SCENE"
    RESOLVED = "RESOLVED"
    RESCUED = "RESCUED"
    CANCELLED = "CANCELLED"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category: Mapped[IncidentCategory] = mapped_column(
        Enum(IncidentCategory, name="incidentcategory"), nullable=False, default=IncidentCategory.CRITICAL_TRAPPED
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incidentstatus"), nullable=False, default=IncidentStatus.PENDING
    )
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Backward compatibility attributes & mapped columns
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True, default="+919876543210")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    rain_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_status: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, **kwargs: Any) -> None:
        if "emergency_type" in kwargs and "category" not in kwargs:
            kwargs["category"] = kwargs.pop("emergency_type")
        if "severity" in kwargs and "category" not in kwargs:
            kwargs["category"] = kwargs.pop("severity")
        if "phone" in kwargs and "phone_number" not in kwargs:
            kwargs["phone_number"] = kwargs.pop("phone")
        if "geom" in kwargs and "location" not in kwargs:
            kwargs["location"] = kwargs.pop("geom")
        super().__init__(**kwargs)

    @property
    def phone(self) -> str:
        return self.phone_number or ""

    @phone.setter
    def phone(self, value: str) -> None:
        self.phone_number = value

    @property
    def emergency_type(self) -> IncidentCategory:
        return self.category

    @emergency_type.setter
    def emergency_type(self, value: IncidentCategory) -> None:
        self.category = value

    @property
    def severity(self) -> IncidentCategory:
        return self.category

    @severity.setter
    def severity(self, value: IncidentCategory) -> None:
        self.category = value

    @property
    def geom(self) -> Any:
        return self.location

    @geom.setter
    def geom(self, value: Any) -> None:
        self.location = value

    def to_geojson_feature(self) -> dict[str, Any]:
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.lng or 0.0, self.lat or 0.0],
            },
            "properties": {
                "id": self.id,
                "category": self.category.value if hasattr(self.category, "value") else str(self.category),
                "emergency_type": self.category.value if hasattr(self.category, "value") else str(self.category),
                "status": self.status.value if hasattr(self.status, "value") else str(self.status),
                "accuracy": self.accuracy,
                "notes": self.notes,
                "phone_number": self.phone_number or "",
                "created_at": self.created_at.isoformat() if hasattr(self.created_at, "isoformat") else str(self.created_at),
                "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, "isoformat") else str(self.updated_at),
            },
        }


# Aliases for backward compatibility
CitizenSOS = Incident
SOSIncident = Incident
EmergencyType = IncidentCategory
IncidentSeverity = IncidentCategory
CitizenStatus = IncidentStatus
