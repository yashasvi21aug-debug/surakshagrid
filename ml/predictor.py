from __future__ import annotations

import inspect
import logging
from typing import Any

from app.schemas import FloodRiskRequest
from app.services.ml_service import ml_service

logger = logging.getLogger(__name__)


def preload_static_models() -> bool:
    return True


class FloodRiskPredictor:
    """Predictor delegate using app.services.ml_service.MLInferenceService."""

    def predict_risk(
        self,
        lat: float,
        lng: float,
        rain_rate: float,
        discharge: float,
        soil_moisture: float | None = None,
        elevation: float | None = None,
        drainage_index: float | None = None,
        distance_to_waterway: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        req = FloodRiskRequest(
            lat=lat,
            lng=lng,
            precipitation_rate=rain_rate,
            upstream_discharge=discharge,
            soil_saturation=soil_moisture if soil_moisture is not None else 50.0,
            elevation=elevation if elevation is not None else max(2.0, 90.0 - abs(lat) * 2.5),
            distance_to_waterway=distance_to_waterway if distance_to_waterway is not None else 500.0,
        )
        res = ml_service.predict_flood_risk(req)
        res_dict = res.model_dump()
        res_dict["risk_probability"] = res.inundation_probability
        res_dict["water_rise_meters"] = res.estimated_water_rise_meters
        res_dict["status"] = res.severity_classification
        return res_dict

    def preload_static_models(self) -> bool:
        return True


_predictor = FloodRiskPredictor()


def predict_risk(
    lat: float,
    lng: float,
    rain_rate: float,
    discharge: float,
    soil_moisture: float | None = None,
    elevation: float | None = None,
    drainage_index: float | None = None,
    distance_to_waterway: float | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Delegate function to _predictor instance supporting test monkeypatching."""
    kwargs_passed: dict[str, Any] = {}
    if soil_moisture is not None:
        kwargs_passed["soil_moisture"] = soil_moisture
    if elevation is not None:
        kwargs_passed["elevation"] = elevation
    if drainage_index is not None:
        kwargs_passed["drainage_index"] = drainage_index
    if distance_to_waterway is not None:
        kwargs_passed["distance_to_waterway"] = distance_to_waterway

    try:
        sig = inspect.signature(_predictor.predict_risk)
        params = sig.parameters
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            return _predictor.predict_risk(lat, lng, rain_rate, discharge, **kwargs_passed)
        
        valid_kwargs = {k: v for k, v in kwargs_passed.items() if k in params}
        return _predictor.predict_risk(lat, lng, rain_rate, discharge, **valid_kwargs)
    except Exception:
        return _predictor.predict_risk(lat, lng, rain_rate, discharge)
