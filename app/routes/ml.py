from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ml.predictor import predict_risk

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])


@router.post("/evaluate-risk")
async def evaluate_risk(payload: dict) -> dict:
    try:
        lat = float(payload["lat"])
        lng = float(payload["lng"])
        rain_rate = float(payload["rain_rate"])
        discharge = float(payload["discharge"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lat, lng, rain_rate, and discharge are required",
        ) from None

    return predict_risk(lat=lat, lng=lng, rain_rate=rain_rate, discharge=discharge)
