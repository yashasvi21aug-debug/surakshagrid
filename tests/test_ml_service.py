from __future__ import annotations

import pytest
from app.schemas import FloodRiskRequest, FloodRiskResponse
from app.services.ml_service import MLInferenceService


def test_flood_risk_pydantic_validation():
    req = FloodRiskRequest(
        rain_rate=45.0,
        discharge=900.0,
        elevation=12.0,
        soil_saturation=75.0,
        distance_to_waterway=300.0,
    )
    assert req.precipitation_rate == 45.0
    assert req.upstream_discharge == 900.0
    assert req.elevation == 12.0
    assert req.soil_saturation == 75.0
    assert req.distance_to_waterway == 300.0


def test_ml_inference_service_predict():
    service = MLInferenceService()
    req = FloodRiskRequest(
        elevation=8.0,
        precipitation_rate=80.0,
        soil_saturation=90.0,
        distance_to_waterway=150.0,
        upstream_discharge=1200.0,
    )
    response = service.predict_flood_risk(req)
    assert isinstance(response, FloodRiskResponse)
    assert 0.0 <= response.inundation_probability <= 1.0
    assert response.estimated_water_rise_meters >= 0.0
    assert response.estimated_rise_time_hours > 0.0
    assert response.severity_classification in ("LOW", "MODERATE", "HIGH", "CRITICAL")
    assert response.model_source in ("ml_pipeline_joblib", "rational_runoff_hydrodynamic_fallback", "hydrodynamic_physical_fallback")


def test_ml_inference_service_fallback(tmp_path):
    service = MLInferenceService(model_path=tmp_path / "non_existent_pipeline.joblib")
    req = FloodRiskRequest(
        elevation=15.0,
        precipitation_rate=110.0,
        soil_saturation=85.0,
        distance_to_waterway=200.0,
        upstream_discharge=1100.0,
    )
    response = service.predict_flood_risk(req)
    assert "fallback" in response.model_source
    assert response.severity_classification in ("HIGH", "CRITICAL")
    assert response.confidence_score == 0.86
