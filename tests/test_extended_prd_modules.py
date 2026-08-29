from __future__ import annotations

import pytest
from app.services.ml_drift import ml_drift_monitor
from app.services.shelter_allocation import shelter_allocation_service
from app.services.dedup import sos_dedup_service
from app.services.dam_telemetry import dam_telemetry_service
from app.services.cap_alert import cap_alert_service
from app.services.volunteer_fleet import volunteer_fleet_service
from app.services.sitrep import sitrep_service
from app.services.post_mortem import post_mortem_service


@pytest.mark.asyncio
async def test_ml_drift_monitoring(fake_db):
    """Test ML drift error tracking and retraining trigger logic."""
    res = await ml_drift_monitor.check_drift_and_retrain_if_needed(fake_db)
    assert "mae_m" in res
    assert "retraining_triggered" in res


@pytest.mark.asyncio
async def test_shelter_allocation(fake_db):
    """Test capacity-constrained shelter allocation matching."""
    shelters = await shelter_allocation_service.get_all_shelters_geojson(fake_db)
    assert shelters["type"] == "FeatureCollection"

    alloc = await shelter_allocation_service.allocate_rescued_cluster(28.5355, 77.3910, 4, True, fake_db)
    assert alloc["status"] == "ALLOCATED"
    assert "assigned_shelter" in alloc


@pytest.mark.asyncio
async def test_sos_dedup_and_priority():
    """Test spatial-temporal DBSCAN clustering and composite priority calculation."""
    score = sos_dedup_service.calculate_priority_score(3, True, 1.5)
    assert score > 10.0

    incidents = [
        {"id": "SOS-1", "lat": 28.6321, "lng": 77.4446, "category": "CRITICAL_TRAPPED"},
        {"id": "SOS-2", "lat": 28.6322, "lng": 77.4447, "category": "MEDICAL_EVAC"},
    ]
    clusters = sos_dedup_service.cluster_incidents(incidents, spatial_radius_m=50.0)
    assert len(clusters) == 1
    assert clusters[0]["total_headcount"] == 2


@pytest.mark.asyncio
async def test_dam_telemetry():
    """Test upstream dam water release tracking and wave front arrival prediction."""
    res = await dam_telemetry_service.ingest_discharge_and_predict_surge("Hindon Barrage", 2500.0, 6.0)
    assert res["status"] == "SURGE_PREDICTED"
    assert "evacuation_warning_polygon" in res


@pytest.mark.asyncio
async def test_cap_alerts():
    """Test CAP v1.2 XML and RSS Atom feed generation."""
    xml_str = cap_alert_service.generate_cap_xml()
    assert "<alert" in xml_str
    assert "Hindon &amp; Yamuna Sub-Catchment" in xml_str

    rss_str = cap_alert_service.generate_rss_atom_feed()
    assert "<rss" in rss_str


@pytest.mark.asyncio
async def test_volunteer_fleet(fake_db):
    """Test capability-aware rescue asset dispatch matching."""
    fleet = await volunteer_fleet_service.get_available_fleet_geojson(1.2, fake_db)
    assert fleet["type"] == "FeatureCollection"
    assert fleet["required_vehicle_type"] == "INFLATABLE_BOAT"


@pytest.mark.asyncio
async def test_sitrep_and_post_mortem(fake_db):
    """Test Situation Report generation and spatial archive export."""
    sitrep = await sitrep_service.generate_sitrep(12, "markdown", fake_db)
    assert "markdown" in sitrep

    archive = await post_mortem_service.export_spatial_archive("EVENT-2026", "geojson", fake_db)
    assert archive["type"] == "FeatureCollection"
