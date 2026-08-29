from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import CitizenStatus, EmergencyType


def sanitize_text(value: str) -> str:
    """Strip XSS HTML tags, script vectors, and unprintable characters."""
    if not value:
        return value
    clean = re.sub(r"<[^>]*?>", "", value)
    clean = "".join(ch for ch in clean if ch.isprintable())
    return clean.strip()


class SOSCreateRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=32)
    category: EmergencyType = Field(default=EmergencyType.CRITICAL_TRAPPED)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    accuracy: float | None = Field(default=None, ge=0.0)
    notes: str | None = Field(default=None, max_length=500)

    # Aliases / Legacy fields for backward compatibility
    emergencyType: EmergencyType | None = Field(default=None)
    lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    lng: float | None = Field(default=None, ge=-180.0, le=180.0)
    rainRate: float | None = Field(default=None, ge=0.0)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        clean_val = sanitize_text(value)
        digits = "".join(ch for ch in clean_val if ch.isdigit())
        if len(digits) < 8:
            raise ValueError("phone must contain at least 8 digits")
        return clean_val

    @model_validator(mode="before")
    @classmethod
    def alias_sos_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "emergencyType" in values and ("category" not in values or values.get("category") is None):
                values["category"] = values["emergencyType"]
            if "lat" in values and ("latitude" not in values or values.get("latitude") is None):
                values["latitude"] = values["lat"]
            if "lng" in values and ("longitude" not in values or values.get("longitude") is None):
                values["longitude"] = values["lng"]
            if "latitude" in values and ("lat" not in values or values.get("lat") is None):
                values["lat"] = values["latitude"]
            if "longitude" in values and ("lng" not in values or values.get("lng") is None):
                values["lng"] = values["longitude"]
        return values


class SOSStatusUpdate(BaseModel):
    status: CitizenStatus


class SOSListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    min_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    max_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    min_lng: float | None = Field(default=None, ge=-180.0, le=180.0)
    max_lng: float | None = Field(default=None, ge=-180.0, le=180.0)


class NearbySOSQuery(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    radius_km: float = Field(..., gt=0.0, le=100.0)


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


class FloodRiskRequest(BaseModel):
    elevation: float = Field(default=25.0, ge=-50.0, le=9000.0, description="Elevation above sea level in meters")
    precipitation_rate: float = Field(default=0.0, ge=0.0, le=1000.0, description="Precipitation rate in mm/h")
    soil_saturation: float = Field(default=50.0, ge=0.0, le=100.0, description="Soil saturation percentage")
    distance_to_waterway: float = Field(default=500.0, ge=0.0, le=100000.0, description="Distance to nearest river or waterway in meters")
    upstream_discharge: float = Field(default=250.0, ge=0.0, le=50000.0, description="Upstream river discharge rate in m³/s")
    lat: float | None = Field(default=28.6321, ge=-90.0, le=90.0)
    lng: float | None = Field(default=77.4446, ge=-180.0, le=180.0)

    model_config = ConfigDict(populate_by_name=True)

    @property
    def distance_to_drainage(self) -> float:
        return self.distance_to_waterway

    @model_validator(mode="before")
    @classmethod
    def alias_legacy_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "rain_rate" in values and "precipitation_rate" not in values:
                values["precipitation_rate"] = values["rain_rate"]
            if "discharge" in values and "upstream_discharge" not in values:
                values["upstream_discharge"] = values["discharge"]
            if "distance_to_drainage" in values and "distance_to_waterway" not in values:
                values["distance_to_waterway"] = values["distance_to_drainage"]
            if "soil_saturation" in values and isinstance(values["soil_saturation"], (int, float)) and 0.0 < values["soil_saturation"] <= 1.0:
                values["soil_saturation"] = values["soil_saturation"] * 100.0
        return values


class FloodRiskResponse(BaseModel):
    inundation_probability: float = Field(..., ge=0.0, le=1.0)
    estimated_water_rise_meters: float = Field(..., ge=0.0)
    estimated_rise_time_hours: float = Field(..., ge=0.0)
    severity_classification: str = Field(..., description="Severity level: LOW, MODERATE, HIGH, CRITICAL")
    status: str = Field(default="LOW", description="Legacy alias for severity_classification")
    should_flag_flood_polygon: bool
    model_source: str = Field(..., description="ml_pipeline_joblib or hydrodynamic_physical_fallback")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    features_evaluated: dict[str, float]
    risk_probability: float | None = None
    water_rise_meters: float | None = None
    lat: float | None = None
    lng: float | None = None


class EvasiveRouteRequest(BaseModel):
    origin: tuple[float, float] = Field(..., description="[longitude, latitude] of origin point")
    destination: tuple[float, float] = Field(..., description="[longitude, latitude] of destination point")
    avoid_water_depth_m: float = Field(default=0.3, ge=0.0, description="Minimum water depth in meters to avoid")

    @field_validator("origin", "destination")
    @classmethod
    def validate_coordinates(cls, coords: tuple[float, float]) -> tuple[float, float]:
        lng, lat = coords
        if not (-180.0 <= lng <= 180.0):
            raise ValueError(f"Longitude {lng} outside valid range [-180, 180]")
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude {lat} outside valid range [-90, 90]")
        return coords


class EvasiveRouteResponse(BaseModel):
    status: str = Field(..., description="safety classification: safe, rerouted, or warning")
    safe_bypass_geojson: dict[str, Any] = Field(..., description="GeoJSON LineString feature or geometry")
    distance_km: float = Field(..., ge=0.0)
    estimated_travel_time_mins: float = Field(..., ge=0.0)
    flood_zones_considered: int = Field(default=0)
    intersections_avoided: int = Field(default=0)


class LoginRequest(BaseModel):
    officer_id: str | None = None
    email: str | None = None
    badge_id: str | None = None
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    officer_id: str
    role: str
