from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    CITIZEN = "CITIZEN"
    RESPONDER = "RESPONDER"
    DISPATCHER = "DISPATCHER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CITIZEN, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "phone_number": self.phone_number,
            "role": self.role.value,
            "is_active": self.is_active,
            "lat": self.lat,
            "lng": self.lng,
            "created_at": self.created_at.isoformat(),
        }
