from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GaugeStatus(str, enum.Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class SensorTelemetry(Base):
    __tablename__ = "sensor_telemetry"

    sensor_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    water_level_m: Mapped[float] = mapped_column(Float, nullable=False, default=1.5)
    threshold_m: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Backward compatibility attributes & properties
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[GaugeStatus] = mapped_column(
        Enum(GaugeStatus, name="gaugestatus"), default=GaugeStatus.NORMAL, nullable=False
    )

    @property
    def id(self) -> str:
        return self.sensor_id

    @id.setter
    def id(self, value: str) -> None:
        self.sensor_id = value

    @property
    def sensor_name(self) -> str:
        return self.name

    @sensor_name.setter
    def sensor_name(self, value: str) -> None:
        self.name = value

    @property
    def warning_threshold_m(self) -> float:
        return self.threshold_m

    @warning_threshold_m.setter
    def warning_threshold_m(self, value: float) -> None:
        self.threshold_m = value

    @property
    def current_water_level_m(self) -> float:
        return self.water_level_m

    @current_water_level_m.setter
    def current_water_level_m(self, value: float) -> None:
        self.water_level_m = value

    @property
    def last_ping(self) -> datetime:
        return self.timestamp

    @last_ping.setter
    def last_ping(self, value: datetime) -> None:
        self.timestamp = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "id": self.sensor_id,
            "name": self.name,
            "sensor_name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "water_level_m": self.water_level_m,
            "current_water_level_m": self.water_level_m,
            "threshold_m": self.threshold_m,
            "warning_threshold_m": self.threshold_m,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
            "last_ping": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
        }


# Aliases for backward compatibility
IoTWaterGauge = SensorTelemetry
SensorGauge = SensorTelemetry
