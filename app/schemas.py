from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.gis_models import CitizenStatus, EmergencyType


class SOSCreateRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=32)
    emergencyType: EmergencyType = Field(..., alias="emergencyType")
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    rainRate: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 8:
            raise ValueError("phone must contain at least 8 digits")
        return value.strip()


class SOSStatusUpdate(BaseModel):
    status: CitizenStatus


class SOSListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    min_lat: float | None = Field(default=None, ge=-90, le=90)
    max_lat: float | None = Field(default=None, ge=-90, le=90)
    min_lng: float | None = Field(default=None, ge=-180, le=180)
    max_lng: float | None = Field(default=None, ge=-180, le=180)


class NearbySOSQuery(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(..., gt=0, le=100)


class SOSResponse(BaseModel):
    id: str
    phone_number: str
    emergency_type: str
    lat: float
    lng: float
    rain_rate: float | None = None
    risk_status: str | None = None
    status: str
    timestamp: str

    model_config = ConfigDict(from_attributes=True)


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    properties: dict[str, Any]
    geometry: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]
