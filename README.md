# 🛡️ SurakshaGrid (PRD v1.0.0)
> **AI-Powered Flood Disaster Incident Command, Safe Corridor Routing, & Digital Twin Platform**

SurakshaGrid is a production-grade, real-time disaster management and emergency response system tailored for extreme urban flood events along high-risk river basin sub-catchments (such as the Hindon and Yamuna river basins). The platform bridges citizen distress telemetry, IoT river gauge metrics, Sentinel-1 Synthetic Aperture Radar (SAR) flood extent extraction, and dynamic evasive routing for field rescue operators (NDRF).

---

## 🏗️ System Architecture & Data Flow

```text
[ Citizen PWA ]          [ IoT River Gauges ]          [ Copernicus / AWS ]
(Offline Tile Cache)      (Precipitation & Δh/Δt)       (Sentinel-1 SAR GRD)
        │                          │                             │
        ▼                          ▼                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   SurakshaGrid FastAPI Engine (v1.0.0)                 │
│  - Security & OWASP Headers       - Prometheus Telemetry Metrics       │
│  - SlowAPI Rate Limiter          - Hydrology XGBoost Model            │
│  - PostGIS Spatial Indexing      - OSRM Safe Corridor Engine          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Real-Time WebSockets (/ws) <200ms
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  EOC Tactical Command Dashboard (Next.js 14)           │
│  - MapLibre GL Tactical Map      - Zustand Global State Store          │
│  - Turn-by-Turn Maneuver Cards   - Historical 24h Time-Lapse Replay    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack Breakdown

- **Backend Framework:** FastAPI 0.109+, Python 3.11/3.14, AsyncIO, Uvicorn, SlowAPI rate limiting.
- **Database & Spatial Engine:** PostgreSQL 16 + PostGIS 3.4 (GeoAlchemy2, SQLAlchemy 2.0 Async, GIST spatial indexing).
- **Machine Learning & Remote Sensing:** XGBoost 2.0, Rasterio, NumPy, Shapely (Lee speckle filtering & Otsu radiometric thresholding).
- **Routing & Navigation:** OSRM (Open Source Routing Machine) evasive corridor engine avoiding inundated polygons.
- **Frontend Architecture:** Next.js 14 (App Router), TypeScript, TailwindCSS, MapLibre GL JS, Zustand state management.
- **Observability & Ops:** Prometheus Instrumentator (`/metrics`), Structured JSON Logging with `X-Request-ID` correlation IDs.

---

## 🚀 Local Development Setup

### 1. Run with Docker Compose (Recommended)
Launch the complete microservice stack (FastAPI, PostGIS, OSRM Engine, Next.js Frontend) with a single command:

```bash
docker compose up --build
```

- **Next.js Frontend:** `http://localhost:3000`
- **FastAPI Backend:** `http://localhost:8000`
- **OpenAPI / Swagger Specs:** `http://localhost:8000/docs`
- **Prometheus Metrics:** `http://localhost:8000/metrics`

### 2. Manual Local Setup

```bash
# 1. Clone & setup Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Start PostgreSQL/PostGIS database
docker run -d --name suraksha-postgis -p 5432:5432 -e POSTGRES_DB=surakshagrid -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres postgis/postgis:16-3.4

# 3. Apply database migrations
python -m app migrate

# 4. Launch FastAPI server
uvicorn app.main:app --reload --port 8000
```

---

## ☁️ Render Production Deployment Guide

SurakshaGrid is pre-configured for automated deployment on Render via [`render.yaml`](file:///c:/Dev/SurakshaGrid/surakshagrid/render.yaml).

### Step-by-Step Render Deployment:
1. Connect your GitHub repository to **Render Cloud Console**.
2. Select **New > Blueprint** and select `render.yaml`.
3. Render automatically provisions:
   - `surakshagrid-db`: Managed PostgreSQL + PostGIS database.
   - `surakshagrid-api`: Web Service running FastAPI.
   - `surakshagrid-frontend`: Static Site running Next.js.
   - `surakshagrid-daily-backup`: Cron Job running daily spatial database dumps (`0 2 * * *`).

---

## 📡 Key REST API Reference (`/api/v1/*`)

| Method | Endpoint | Description | Request Payload / Params |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/sos` | Ingest citizen distress call | `{ "category": "CRITICAL_TRAPPED", "lat": 28.6321, "lng": 77.4446, "notes": "Stranded" }` |
| `POST` | `/api/v1/routes/safe-corridor` | Compute evasive safe corridor | `{ "start_lat": 28.6590, "start_lng": 77.2490, "end_lat": 28.6321, "end_lng": 77.4446 }` |
| `GET` | `/api/v1/spatial/inundation` | Query active flood GeoJSON | `?bbox=77.2,28.5,77.6,28.8` |
| `GET` | `/api/v1/spatial/sensors` | Fetch IoT gauge telemetry | None |
| `GET` | `/api/v1/spatial/temporal-playback` | Historical 24h time-lapse replay | `?step_hours=1` |
| `PATCH` | `/api/v1/dispatch/incident/{id}/status` | Update incident status | `{ "status": "RESOLVED", "officer_notes": "Rescue completed" }` |
| `GET` | `/api/v1/health/ready` | Deep readiness probe | Checks PostGIS, ML Model, and OSRM reachability |
| `GET` | `/metrics` | Prometheus telemetry metrics | Standard Prometheus scrape format |

### Sample cURL Commands

```bash
# 1. Submit Emergency Citizen SOS
curl -X POST "http://localhost:8000/api/v1/sos" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+91-9876543210", "category": "CRITICAL_TRAPPED", "lat": 28.6321, "lng": 77.4446}'

# 2. Compute Dynamic Safe Corridor Route
curl -X POST "http://localhost:8000/api/v1/routes/safe-corridor" \
  -H "Content-Type: application/json" \
  -d '{"start_lat": 28.6590, "start_lng": 77.2490, "end_lat": 28.6321, "end_lng": 77.4446, "vehicle_type": "boat"}'
```

---

## 🌊 Disaster Simulation CLI

SurakshaGrid includes a CLI harness to simulate synthetic flood progression, rising gauge telemetry, and citizen SOS dispatches:

```bash
# Run 60-second flood disaster scenario simulation
python -m app run-simulation --duration 60 --interval 2.0
```

---

## 🧪 Testing & Verification

```bash
# Run full Pytest backend test suite (77+ passed)
python -m pytest

# Run E2E Architecture Verification Script (PRD FR-1 to FR-5)
python scripts/verify_prd_flow.py

# Run Locust High-Concurrency Load Benchmark
locust -f benchmarks/locustfile.py --headless -u 500 -r 20 -t 60s --host http://localhost:8000
```
