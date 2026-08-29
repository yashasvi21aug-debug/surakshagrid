from __future__ import annotations

import random
import time
from locust import HttpUser, between, task


class CitizenSOSUser(HttpUser):
    """Simulates 1,000 concurrent stranded citizens submitting distress telemetry."""

    wait_time = between(0.1, 1.0)

    @task(3)
    def submit_emergency_sos(self) -> None:
        categories = ["CRITICAL_TRAPPED", "MEDICAL_EVAC", "FOOD_WATER"]
        lat = 28.6321 + (random.random() - 0.5) * 0.1
        lng = 77.4446 + (random.random() - 0.5) * 0.1

        payload = {
            "category": random.choice(categories),
            "emergencyType": random.choice(categories),
            "phone": f"+91-98{random.randint(10000000, 99999999)}",
            "lat": lat,
            "lng": lng,
            "latitude": lat,
            "longitude": lng,
            "accuracy": random.uniform(3.0, 15.0),
            "rainRate": random.uniform(20.0, 90.0),
            "notes": "Locust load test synthetic emergency payload",
        }

        with self.client.post(
            "/api/v1/sos/",
            json=payload,
            catch_response=True,
            name="POST /api/v1/sos",
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")

    @task(1)
    def fetch_inundation_geojson(self) -> None:
        self.client.get("/api/v1/spatial/inundation", name="GET /api/v1/spatial/inundation")

    @task(1)
    def fetch_river_sensors(self) -> None:
        self.client.get("/api/v1/spatial/sensors", name="GET /api/v1/spatial/sensors")
