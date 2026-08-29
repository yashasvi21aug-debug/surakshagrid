import pytest
from app.schemas import FloodRiskRequest
from app.services.ml_service import ml_service


def test_predict_subcatchment_risk():
    request = FloodRiskRequest(
        precipitation_rate=45.0,
        upstream_discharge=1200.0,
        soil_saturation=85.0,
        elevation=12.0,
        distance_to_waterway=350.0,
    )
    response = ml_service.predict_subcatchment_risk(request)
    assert response.inundation_probability >= 0.0
    assert response.estimated_water_rise_meters >= 0.0
    assert response.severity_classification in ("LOW", "MODERATE", "HIGH", "CRITICAL")
    assert response.model_source in ("xgboost_hydrology_json", "ml_pipeline_joblib", "rational_runoff_hydrodynamic_fallback")


@pytest.mark.asyncio
async def test_predict_inundation_route_endpoint(client):
    payload = {
        "precipitation_rate": 55.0,
        "upstream_discharge": 1500.0,
        "soil_saturation": 90.0,
        "elevation": 10.0,
        "distance_to_waterway": 200.0,
    }
    response = await client.post("/api/v1/ml/predict-inundation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "inundation_probability" in data
    assert "estimated_water_rise_meters" in data
    assert "severity_classification" in data
