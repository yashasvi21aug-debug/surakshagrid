from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, status, Body

from app.schemas import FloodRiskRequest, FloodRiskResponse
from app.services.ml_service import ml_service
from ml.predictor import predict_risk

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])


@router.post("/predict", response_model=FloodRiskResponse)
async def predict_flood_risk(request: FloodRiskRequest) -> FloodRiskResponse:
    """Execute dynamic machine learning prediction for live hydro-meteorological feature vectors."""
    return ml_service.predict_flood_risk(request)


@router.post("/predict-inundation", response_model=FloodRiskResponse)
async def predict_inundation_risk(request: FloodRiskRequest) -> FloodRiskResponse:
    """Predict 6-12 hour subcatchment flood inundation probability and estimated water rise."""
    return ml_service.predict_subcatchment_risk(request)


@router.post("/evaluate-risk")
async def evaluate_risk(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Perform dynamic machine learning flood risk evaluation for legacy request payloads."""
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must be a JSON object",
        )

    has_lat = "lat" in payload
    has_lng = "lng" in payload
    has_rain = "rain_rate" in payload or "precipitation_rate" in payload or "precipitation_mm_h" in payload
    has_discharge = "discharge" in payload or "upstream_discharge" in payload or "upstream_river_discharge_m3s" in payload

    if not (has_lat and has_lng and has_rain and has_discharge):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lat, lng, rain_rate, and discharge are required",
        )

    try:
        request_model = FloodRiskRequest(**payload)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid feature vector payload: {err}",
        ) from err

    return predict_risk(
        lat=request_model.lat or 28.6321,
        lng=request_model.lng or 77.4446,
        rain_rate=request_model.precipitation_rate,
        discharge=request_model.upstream_discharge,
        soil_moisture=request_model.soil_saturation,
        elevation=request_model.elevation,
        distance_to_waterway=request_model.distance_to_waterway,
    )
