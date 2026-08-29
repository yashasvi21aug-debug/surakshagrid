from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Enum, Float, Integer, String
from app.models.base import Base


class IncidentSeverity(str, enum.Enum):
    CRITICAL_TRAPPED = "CRITICAL_TRAPPED"
    MEDICAL_EVAC = "MEDICAL_EVAC"
    FOOD_WATER = "FOOD_WATER"
    INFRASTRUCTURE_DAMAGE = "INFRASTRUCTURE_DAMAGE"


class IncidentStatus(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    RESOLVED = "RESOLVED"


class GaugeStatus(str, enum.Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Incident(Base):
    """PostGIS Point geometry model for citizen emergency SOS incidents."""

    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(32), nullable=False)
    severity = Column(Enum(IncidentSeverity), default=IncidentSeverity.CRITICAL_TRAPPED, nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.PENDING, nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    rain_rate = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_geojson_feature(self) -> dict:
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.lng or 0.0, self.lat or 0.0],
            },
            "properties": {
                "id": self.id,
                "phone": self.phone,
                "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
                "status": self.status.value if hasattr(self.status, "value") else str(self.status),
                "rain_rate": self.rain_rate,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            },
        }


class FloodPolygon(Base):
    """PostGIS Polygon / MultiPolygon geometry model for active flood inundation zones."""

    __tablename__ = "flood_polygons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_name = Column(String(128), default="Inundation_Zone", nullable=False)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=True)
    depth_m = Column(Float, default=0.5, nullable=False)
    severity = Column(String(32), default="HIGH", nullable=False)
    risk_score = Column(Float, default=0.85, nullable=False)
    predicted_horizon_hours = Column(Integer, default=6, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_geojson_feature(self) -> dict:
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [],
            },
            "properties": {
                "id": self.id,
                "zone_name": self.zone_name,
                "depth_m": self.depth_m,
                "severity": self.severity,
                "risk_score": self.risk_score,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            },
        }


class SensorGauge(Base):
    """PostGIS Point geometry model for river water level telemetry sensors."""

    __tablename__ = "sensor_gauges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sensor_name = Column(String(128), nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    water_level_m = Column(Float, default=1.5, nullable=False)
    warning_threshold_m = Column(Float, default=2.5, nullable=False)
    threshold_status = Column(Enum(GaugeStatus), default=GaugeStatus.NORMAL, nullable=False)
    last_ping = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
