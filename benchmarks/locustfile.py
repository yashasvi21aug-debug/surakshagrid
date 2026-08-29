import random
import time
from locust import HttpUser, task, between, events
import websocket
import json
import logging

logger = logging.getLogger(__name__)

# Bounding box bounds for synthetic telemetry jitter
MIN_LAT, MAX_LAT = 28.5000, 28.7000
MIN_LNG, MAX_LNG = 77.2000, 77.5000
CATEGORIES = ["CRITICAL_TRAPPED", "MEDICAL_EVAC", "FOOD_WATER", "INFRASTRUCTURE_DAMAGE"]


class CitizenUser(HttpUser):
    """Simulates stranded citizens submitting high-frequency SOS distress calls under flood stress."""
    wait_time = between(1, 3)

    @task(3)
    def submit_sos(self):
        lat = round(random.uniform(MIN_LAT, MAX_LAT), 4)
        lng = round(random.uniform(MIN_LNG, MAX_LNG), 4)
        category = random.choice(CATEGORIES)

        payload = {
            "phone_number": f"+91-98{random.randint(10000000, 99999999)}",
            "category": category,
            "lat": lat,
            "lng": lng,
            "notes": f"Locust Load Test - Stranded at coordinate ({lat}, {lng})",
            "accuracy": round(random.uniform(3.0, 15.0), 1),
        }

        with self.client.post("/api/v1/sos", json=payload, catch_response=True) as response:
            if response.status_code in (200, 201):
                response.success()
            else:
                response.failure(f"SOS Ingest Failed: Status {response.status_code}")


class DashboardOfficerUser(HttpUser):
    """Simulates EOC Command Center officers constantly monitoring live spatial hazards and sensors."""
    wait_time = between(0.5, 2)

    def on_start(self):
        # Open persistent WebSocket connection
        try:
            ws_host = self.host.replace("http://", "ws://").replace("https://", "wss://")
            self.ws = websocket.create_connection(f"{ws_host}/ws", timeout=2)
        except Exception as e:
            self.ws = None

    def on_stop(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass

    @task(3)
    def poll_inundation_polygons(self):
        with self.client.get("/api/v1/spatial/inundation", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Inundation Polygons Query Failed: {response.status_code}")

    @task(2)
    def poll_river_sensors(self):
        with self.client.get("/api/v1/spatial/sensors", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"River Sensors Query Failed: {response.status_code}")

    @task(1)
    def receive_ws_frame(self):
        if self.ws:
            try:
                self.ws.settimeout(0.1)
                msg = self.ws.recv()
                events.request.fire(
                    request_type="WebSocket",
                    name="/ws:recv",
                    response_time=5,
                    response_length=len(msg),
                    exception=None,
                )
            except Exception:
                pass


class RescueOperatorUser(HttpUser):
    """Simulates NDRF rescue boat operators requesting safe corridor navigation routes."""
    wait_time = between(2, 5)

    @task
    def request_safe_corridor(self):
        payload = {
            "start_lat": 28.6590,
            "start_lng": 77.2490,
            "end_lat": round(random.uniform(MIN_LAT, MAX_LAT), 4),
            "end_lng": round(random.uniform(MIN_LNG, MAX_LNG), 4),
            "vehicle_type": "boat",
        }

        with self.client.post("/api/v1/routes/safe-corridor", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Safe Corridor Route Computation Failed: {response.status_code}")
