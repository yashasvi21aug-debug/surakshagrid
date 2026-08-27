from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmergencyType(str, Enum):
    CRITICAL_TRAPPED = "CRITICAL_TRAPPED"
    MEDICAL_EVAC = "MEDICAL_EVAC"
    FOOD_WATER = "FOOD_WATER"


class CitizenStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    RESOLVED = "RESOLVED"


class GaugeStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class RescueUnitStatus(str, Enum):
    STANDBY = "STANDBY"
    EN_ROUTE = "EN_ROUTE"
    ON_SITE = "ON_SITE"


class CitizenSOS(Base):
    __tablename__ = "citizen_sos"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    emergency_type: Mapped[EmergencyType] = mapped_column(
        String(32),
        nullable=False,
    )
    location: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    rain_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[CitizenStatus] = mapped_column(
        String(32),
        nullable=False,
        default=CitizenStatus.PENDING,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )


class InundationZone(Base):
    __tablename__ = "inundation_zone"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        index=True,
    )
    zone_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    polygon: Mapped[object] = mapped_column(
        Geometry("POLYGON", srid=4326, spatial_index=True),
        nullable=False,
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_water_rise: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )


class IoTWaterGauge(Base):
    __tablename__ = "iot_water_gauge"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        index=True,
    )
    sensor_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    location: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    current_water_level_m: Mapped[float] = mapped_column(Float, nullable=False)
    warning_threshold_m: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[GaugeStatus] = mapped_column(
        String(32),
        nullable=False,
        default=GaugeStatus.NORMAL,
        index=True,
    )
    last_ping: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )


class RescueUnit(Base):
    __tablename__ = "rescue_unit"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        index=True,
    )
    unit_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    current_location: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    assigned_sos_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[RescueUnitStatus] = mapped_column(
        String(32),
        nullable=False,
        default=RescueUnitStatus.STANDBY,
        index=True,
    )
