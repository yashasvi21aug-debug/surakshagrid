# 🚨 SurakshaGrid Disaster Incident Response Runbook (PRD v1.0.0)
> **Standard Operating Procedures (SOP) for Emergency Operations Center (EOC) Officers & DevOps Engineers**

---

## 📋 Table of Contents
1. [Pre-Disaster Phase (Preparation & Monitoring)](#1-pre-disaster-phase-preparation--monitoring)
2. [Active Flood Phase (Emergency Operations & Dispatch)](#2-active-flood-phase-emergency-operations--dispatch)
3. [Degraded Network Mode (Contingencies & Fallbacks)](#3-degraded-network-mode-contingencies--fallbacks)
4. [Incident Recovery & Post-Mortem Analysis](#4-incident-recovery--post-mortem-analysis)

---

## 1. 🌤️ Pre-Disaster Phase (Preparation & Monitoring)

### 1.1 Trigger Predictive Hydrological Sweeps
Run automated XGBoost precipitation sweeps across river sub-catchments 12–24 hours prior to forecasted landfall:

```bash
# Trigger XGBoost inundation prediction sweep
curl -X POST "http://localhost:8000/api/v1/ml/trigger-forecast" \
  -H "Content-Type: application/json" \
  -d '{"sub_catchment": "Hindon_Basin_01", "lead_time_hours": 24}'
```

### 1.2 Baseline PostGIS Geometry & Spatial Health Check
Verify PostGIS spatial index validity and geometry SRID 4326 compliance:

```bash
# Execute deep readiness probe validating database, ML models, and OSRM
curl -s "http://localhost:8000/api/v1/health/ready" | jq .
```

### 1.3 IoT River Gauge Sensor Calibration
Verify that river level sensors (e.g. `G-HINDON-01`) report active telemetry and correct alert thresholds ($h \ge 2.50\text{m}$):

```bash
# Fetch live sensor readings
curl -s "http://localhost:8000/api/v1/spatial/sensors" | jq .
```

---

## 2. 🌊 Active Flood Phase (Emergency Operations & Dispatch)

### 2.1 Manual Sentinel-1 SAR Imagery Ingestion
When optical satellite vision is obscured by cloud cover during heavy storms, ingest new Sentinel-1 SAR GRD rasters manually:

```bash
# Ingest Sentinel-1 GeoTIFF from S3 or direct file upload
curl -X POST "http://localhost:8000/api/v1/spatial/sar-ingest?s3_uri=s3://sentinel-s1-l1c/GRD_ACTIVE_STORM.tif"
```

### 2.2 WebSocket Broadcast & Latency Monitoring
Ensure live WebSocket frames (`NEW_INCIDENT`, `HAZARD_LAYER_UPDATE`) deliver within 200 ms:

- Monitor Prometheus gauge `active_websocket_connections` at `http://localhost:8000/metrics`.
- Check browser console on Command Dashboard (`/dashboard`) for reconnect heartbeat indicators.

### 2.3 NDRF Field Unit Dispatch & Corridor Allocation
Assign trapped citizens (`CRITICAL_TRAPPED`) to nearest available NDRF amphibious rescue units:

```bash
# Assign rescue team & generate safe corridor
curl -X POST "http://localhost:8000/api/v1/dispatch/assign" \
  -H "Content-Type: application/json" \
  -d '{
        "sos_id": "INCIDENT-9921",
        "unit_id": "NDRF-ALPHA-01",
        "start_lat": 28.6590,
        "start_lng": 77.2490
      }'
```

---

## 3. 📉 Degraded Network Mode (Contingencies & Fallbacks)

### 3.1 Citizen PWA Offline Mode & IndexedDB Caching
- When cell towers fail, the citizen portal (`/citizen`) switches to local IndexedDB tile cache (zoom 10–16).
- Pending SOS distress dispatches are safely queued in `tileCache.ts` and automatically retried when connectivity restores.

### 3.2 OSRM Heuristic Safe Route Fallback
If the live OSRM server experiences high latency under heavy surge, the backend automatically switches to PostGIS `ST_Buffer` + `ST_Difference` heuristic safe path generation (`app/services/routing.py`).

---

## 4. 📊 Incident Recovery & Post-Mortem Analysis

### 4.1 Export Post-Disaster Spatial Audit Logs
Extract full incident histories and rescue route logs for official state disaster post-mortems:

```sql
-- Export incident resolution timeline
SELECT id, category, status, lat, lng, created_at, resolved_at
FROM incidents
ORDER BY created_at DESC;

-- Export safe corridor route logs
SELECT log_id, unit_id, incident_id, distance_km, travel_time_mins, created_at
FROM route_logs;
```

### 4.2 Generate Hydrological Model Performance Report
Compare predicted XGBoost flood depths against actual PostGIS SAR vector polygons to calculate RMSE and precision metrics for model retraining.
