from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.flood_zone import InundationZone
from app.models.incident import CitizenSOS, CitizenStatus, EmergencyType


class GaugeStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class RescueUnitStatus(str, Enum):
    STANDBY = "STANDBY"
    EN_ROUTE = "EN_ROUTE"
    ON_SITE = "ON_SITE"


class IoTWaterGauge(Base):
    __tablename__ = "iot_water_gauge"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        index=True,
    )
    sensor_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    unit_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    current_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_sos_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[RescueUnitStatus] = mapped_column(
        String(32),
        nullable=False,
        default=RescueUnitStatus.STANDBY,
        index=True,
    )
