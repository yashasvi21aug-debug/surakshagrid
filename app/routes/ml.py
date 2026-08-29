from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, status

from ml.predictor import predict_risk

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])


@router.post("/evaluate-risk")
async def evaluate_risk(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        lat = float(payload["lat"])
        lng = float(payload["lng"])
        
        rain_val = payload.get("rain_rate", payload.get("precipitation_mm_h"))
        dis_val = payload.get("discharge", payload.get("upstream_discharge", payload.get("upstream_river_discharge_m3s")))

        if rain_val is None or dis_val is None:
            raise KeyError("rain_rate and discharge are required")

        rain_rate = float(rain_val)
        discharge = float(dis_val)
    except (KeyError, TypeError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"lat, lng, rain_rate, and discharge are required: {err}",
        ) from err

    kwargs: dict[str, Any] = {}
    if "soil_moisture" in payload:
        kwargs["soil_moisture"] = float(payload["soil_moisture"])
    if "elevation" in payload:
        kwargs["elevation"] = float(payload["elevation"])
    if "drainage_index" in payload:
        kwargs["drainage_index"] = float(payload["drainage_index"])

    return predict_risk(
        lat=lat,
        lng=lng,
        rain_rate=rain_rate,
        discharge=discharge,
        **kwargs,
    )
