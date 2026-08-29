from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RescueUnitStatus(str, enum.Enum):
    STANDBY = "STANDBY"
    EN_ROUTE = "EN_ROUTE"
    ON_SITE = "ON_SITE"


class RouteLog(Base):
    __tablename__ = "route_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    origin: Mapped[str] = mapped_column(String(255), nullable=False, default="[0.0, 0.0]")
    destination: Mapped[str] = mapped_column(String(255), nullable=False, default="[0.0, 0.0]")
    waypoints: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_min: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avoided_flood_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="safe")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Backward compatibility attributes & properties
    origin_lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    @property
    def duration_mins(self) -> float:
        return self.duration_min

    @duration_mins.setter
    def duration_mins(self, value: float) -> None:
        self.duration_min = value

    @property
    def intersections_avoided(self) -> int:
        return self.avoided_flood_count

    @intersections_avoided.setter
    def intersections_avoided(self, value: int) -> None:
        self.avoided_flood_count = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "origin": self.origin,
            "destination": self.destination,
            "waypoints": self.waypoints,
            "status": self.status,
            "distance_km": self.distance_km,
            "duration_min": self.duration_min,
            "duration_mins": self.duration_min,
            "avoided_flood_count": self.avoided_flood_count,
            "intersections_avoided": self.avoided_flood_count,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, "isoformat") else str(self.created_at),
        }


class Shelter(Base):
    __tablename__ = "shelters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class RescueUnit(Base):
    __tablename__ = "rescue_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    current_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_sos_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[RescueUnitStatus] = mapped_column(
        Enum(RescueUnitStatus, name="rescueunitstatus"), default=RescueUnitStatus.STANDBY, nullable=False, index=True
    )
