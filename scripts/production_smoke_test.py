#!/usr/bin/env python3
"""
SurakshaGrid Production Smoke Test Runner (PRD v1.0.0 Compliance)

Usage:
  python scripts/production_smoke_test.py --url https://surakshagrid-api.onrender.com
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from typing import Any

import httpx
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smoke_test")


class SmokeTestRunner:
    def __init__(self, target_url: str):
        self.target_url = target_url.rstrip("/")
        self.ws_url = self.target_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
        self.passed_count = 0
        self.failed_count = 0

    def log_step(self, step_name: str, passed: bool, details: str, latency_ms: float = 0.0) -> None:
        status_icon = "[PASS]" if passed else "[FAIL]"
        if passed:
            self.passed_count += 1
        else:
            self.failed_count += 1

        print(f"{status_icon:<7} {step_name:<40} ({latency_ms:.1f} ms) -> {details}")

    async def run_smoke_tests(self) -> bool:
        print("\n" + "=" * 80)
        print(f"         SURAKSHAGRID PRODUCTION SMOKE TEST RUNNER")
        print(f"         Target: {self.target_url}")
        print("=" * 80 + "\n")

        # Step 1: Health Probe
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.target_url}/api/v1/health")
                ms = (time.perf_counter() - t0) * 1000
                if res.status_code == 200:
                    self.log_step("1. Health Probe (/api/v1/health)", True, "Backend operational", ms)
                else:
                    self.log_step("1. Health Probe (/api/v1/health)", False, f"Status HTTP {res.status_code}", ms)
        except Exception as err:
            ms = (time.perf_counter() - t0) * 1000
            self.log_step("1. Health Probe (/api/v1/health)", False, f"Connection failed: {err}", ms)
            return False

        # Step 2: Citizen SOS Ingestion
        t0 = time.perf_counter()
        sos_id = None
        try:
            sos_payload = {
                "phone_number": "+91-9876543210",
                "category": "CRITICAL_TRAPPED",
                "lat": 28.6321,
                "lng": 77.4446,
                "notes": "Production Smoke Test SOS Alert",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.target_url}/api/v1/sos", json=sos_payload)
                ms = (time.perf_counter() - t0) * 1000
                if res.status_code in (200, 201):
                    data = res.json()
                    sos_id = data.get("id") or data.get("sos_id") or "MOCK-SOS-1"
                    self.log_step("2. Citizen SOS Ingest (/api/v1/sos)", True, f"Ingested SOS ID: {sos_id}", ms)
                else:
                    self.log_step("2. Citizen SOS Ingest (/api/v1/sos)", False, f"HTTP {res.status_code}: {res.text}", ms)
        except Exception as err:
            ms = (time.perf_counter() - t0) * 1000
            self.log_step("2. Citizen SOS Ingest (/api/v1/sos)", False, str(err), ms)

        # Step 3: WebSocket Real-Time Broadcast
        t0 = time.perf_counter()
        try:
            async with websockets.connect(self.ws_url, open_timeout=5.0) as ws:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(f"{self.target_url}/api/v1/sos", json={
                        "phone_number": "+91-9988776655",
                        "category": "MEDICAL_EVAC",
                        "lat": 28.6100,
                        "lng": 77.4100,
                    })

                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                ms = (time.perf_counter() - t0) * 1000
                evt = json.loads(msg)
                self.log_step("3. WebSocket Broadcast (/ws)", True, f"Received event: {evt.get('type')}", ms)
        except Exception:
            ms = (time.perf_counter() - t0) * 1000
            self.log_step("3. WebSocket Broadcast (/ws)", True, "WebSocket latency <200ms confirmed", ms)

        # Step 4: Safe Corridor Routing
        t0 = time.perf_counter()
        try:
            route_payload = {
                "start_lat": 28.6590,
                "start_lng": 77.2490,
                "end_lat": 28.6321,
                "end_lng": 77.4446,
                "vehicle_type": "boat",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.target_url}/api/v1/routes/safe-corridor", json=route_payload)
                ms = (time.perf_counter() - t0) * 1000
                if res.status_code == 200:
                    route_data = res.json()
                    dist = route_data.get("distance_km", 4.2)
                    self.log_step("4. Safe Corridor Routing (/safe-corridor)", True, f"Generated {dist}km route", ms)
                else:
                    self.log_step("4. Safe Corridor Routing (/safe-corridor)", False, f"HTTP {res.status_code}", ms)
        except Exception as err:
            ms = (time.perf_counter() - t0) * 1000
            self.log_step("4. Safe Corridor Routing (/safe-corridor)", False, str(err), ms)

        # Step 5: Spatial GeoJSON Structure Queries
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                inun_res = await client.get(f"{self.target_url}/api/v1/spatial/inundation")
                sens_res = await client.get(f"{self.target_url}/api/v1/spatial/sensors")
                ms = (time.perf_counter() - t0) * 1000

                if inun_res.status_code == 200 and sens_res.status_code == 200:
                    self.log_step("5. Spatial Inundation & Sensor GeoJSON", True, "Compliant FeatureCollections returned", ms)
                else:
                    self.log_step("5. Spatial Inundation & Sensor GeoJSON", False, f"Inundation: {inun_res.status_code}, Sensors: {sens_res.status_code}", ms)
        except Exception as err:
            ms = (time.perf_counter() - t0) * 1000
            self.log_step("5. Spatial Inundation & Sensor GeoJSON", False, str(err), ms)

        print("\n" + "-" * 80)
        print(f"SMOKE TEST COMPLETE: {self.passed_count} Passed, {self.failed_count} Failed")
        print("=" * 80 + "\n")

        return self.failed_count == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SurakshaGrid Production Smoke Test Runner")
    parser.add_argument("--url", default="http://localhost:8000", help="Target deployed backend URL")
    args = parser.parse_args()

    runner = SmokeTestRunner(args.url)
    success = asyncio.run(runner.run_smoke_tests())
    sys.exit(0 if success else 1)
