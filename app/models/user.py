from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OfficerRole(str, enum.Enum):
    COMMANDER = "COMMANDER"
    FIELD_OPERATOR = "FIELD_OPERATOR"
    DISPATCHER = "DISPATCHER"
    RESPONDER = "RESPONDER"
    CITIZEN = "CITIZEN"
    ADMIN = "ADMIN"


class Officer(Base):
    __tablename__ = "officers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    badge_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    role: Mapped[OfficerRole] = mapped_column(
        Enum(OfficerRole, name="officerrole"), default=OfficerRole.FIELD_OPERATOR, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(120), nullable=True, default="Officer")
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "badge_id": self.badge_id,
            "name": self.name,
            "phone_number": self.phone_number,
            "role": self.role.value if hasattr(self.role, "value") else str(self.role),
            "is_active": self.is_active,
            "lat": self.lat,
            "lng": self.lng,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, "isoformat") else str(self.created_at),
        }


# Aliases for backward compatibility
User = Officer
UserRole = OfficerRole
