from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.models.base import Base


class RouteLog(Base):
    __tablename__ = "route_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    dest_lat = Column(Float, nullable=False)
    dest_lng = Column(Float, nullable=False)
    status = Column(String(50), nullable=False, default="safe")
    distance_km = Column(Float, nullable=False, default=0.0)
    duration_mins = Column(Float, nullable=False, default=0.0)
    intersections_avoided = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "origin": [self.origin_lng, self.origin_lat],
            "destination": [self.dest_lng, self.dest_lat],
            "status": self.status,
            "distance_km": self.distance_km,
            "duration_mins": self.duration_mins,
            "intersections_avoided": self.intersections_avoided,
            "created_at": self.created_at.isoformat(),
        }
