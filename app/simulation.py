from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any

from app.websocket_manager import manager

logger = logging.getLogger(__name__)

# Realistic Topological Coordinates: Hindon-Yamuna NCR River Basin
HINDON_YAMUNA_BASIN_POLYGONS = [
    {
        "zone_name": "Hindon Basin North Lowland",
        "coordinates": [
            [77.3380, 28.6620],
            [77.3620, 28.6620],
            [77.3620, 28.6850],
            [77.3380, 28.6850],
            [77.3380, 28.6620],
        ],
        "base_depth": 0.8,
    },
    {
        "zone_name": "Yamuna Right Bank Floodplain",
        "coordinates": [
            [77.2200, 28.6200],
            [77.2420, 28.6200],
            [77.2420, 28.6480],
            [77.2200, 28.6480],
            [77.2200, 28.6200],
        ],
        "base_depth": 1.2,
    },
    {
        "zone_name": "NCR East Perimeter Canal",
        "coordinates": [
            [77.3970, 28.6960],
            [77.4210, 28.6960],
            [77.4210, 28.7180],
            [77.3970, 28.7180],
            [77.3970, 28.6960],
        ],
        "base_depth": 0.5,
    },
]

SAFE_SHELTERS = [
    {"name": "Hindon High-Ground Relief Shelter", "lat": 28.6812, "lng": 77.3764, "capacity": 450},
    {"name": "Sahibabad Civil Defence Centre", "lat": 28.6765, "lng": 77.3516, "capacity": 300},
    {"name": "NCR East Evacuation School", "lat": 28.7148, "lng": 77.3182, "capacity": 600},
]

WATER_GAUGES = [
    {"sensor_name": "Hindon-01", "lat": 28.6745, "lng": 77.3642, "base_level": 2.2, "warning_threshold": 2.5},
    {"sensor_name": "Yamuna-Delta-02", "lat": 28.6475, "lng": 77.2387, "base_level": 3.1, "warning_threshold": 3.2},
    {"sensor_name": "NCR-West-07", "lat": 28.5931, "lng": 77.1634, "base_level": 1.8, "warning_threshold": 2.3},
]

EMERGENCY_TYPES = ["CRITICAL_TRAPPED", "MEDICAL_EVAC", "FOOD_WATER", "INFRASTRUCTURE_DAMAGE"]


class FloodSimulationHarness:
    """Dynamic Live Simulation Engine for SurakshaGrid Flood Disaster Events."""

    def __init__(self, interval: float = 2.0) -> None:
        self.interval = interval
        self.is_running = False
        self._task: asyncio.Task[None] | None = None
        self.step_count = 0

        # Simulated vehicle locations
        self.vehicles = [
            {"unit_id": "NDRF-BOAT-01", "unit_name": "NDRF Rescue Boat 01", "lat": 28.6590, "lng": 77.2490, "target_lat": 28.6800, "target_lng": 77.3500},
            {"unit_id": "RESCUE-TRUCK-04", "unit_name": "Sahibabad Rescue Truck 04", "lat": 28.6860, "lng": 77.3015, "target_lat": 28.6940, "target_lng": 77.3045},
        ]

    async def start(self, duration_seconds: float | None = None) -> None:
        """Start the async live simulation loop."""
        if self.is_running:
            logger.warning("Simulation harness is already running.")
            return

        self.is_running = True
        self.step_count = 0
        self._task = asyncio.create_task(self._run_loop(duration_seconds))
        logger.info("Started SurakshaGrid live disaster simulation harness.")

    async def stop(self) -> None:
        """Stop the live simulation loop."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped SurakshaGrid live disaster simulation harness.")

    async def _run_loop(self, duration_seconds: float | None = None) -> None:
        start_time = datetime.now(timezone.utc)
        while self.is_running:
            self.step_count += 1
            await self._emit_simulation_tick()

            if duration_seconds is not None:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= duration_seconds:
                    logger.info("Simulation duration of %.1fs reached. Stopping.", duration_seconds)
                    self.is_running = False
                    break

            await asyncio.sleep(self.interval)

    async def _emit_simulation_tick(self) -> None:
        """Execute one simulation tick, broadcasting events across WebSocket rooms."""
        now_str = datetime.now(timezone.utc).isoformat()
        rise_offset = (self.step_count % 30) * 0.08

        # 1. Simulate Water Level Gauge Updates
        gauge_events = []
        for gauge in WATER_GAUGES:
            current_level = round(gauge["base_level"] + rise_offset + random.uniform(-0.05, 0.05), 2)
            gauge_status = (
                "CRITICAL" if current_level >= gauge["warning_threshold"] + 0.8
                else "WARNING" if current_level >= gauge["warning_threshold"]
                else "NORMAL"
            )
            gauge_events.append({
                "sensor_name": gauge["sensor_name"],
                "lat": gauge["lat"],
                "lng": gauge["lng"],
                "current_water_level_m": current_level,
                "warning_threshold_m": gauge["warning_threshold"],
                "status": gauge_status,
                "timestamp": now_str,
            })

        await manager.broadcast_to_rooms({
            "event_type": "WATER_GAUGE_UPDATE",
            "timestamp": now_str,
            "gauges": gauge_events,
        }, ["dashboard", "responders"])

        # 2. Simulate Expanding Inundation Hazard Polygons
        polygon_features = []
        for zone in HINDON_YAMUNA_BASIN_POLYGONS:
            depth = round(zone["base_depth"] + rise_offset, 2)
            risk_score = min(0.99, round(0.5 + depth * 0.15, 2))
            polygon_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [zone["coordinates"]],
                },
                "properties": {
                    "zone_name": zone["zone_name"],
                    "water_depth_m": depth,
                    "risk_score": risk_score,
                    "estimated_water_rise": depth,
                    "timestamp": now_str,
                },
            })

        await manager.broadcast_to_rooms({
            "event_type": "INUNDATION_ZONES_UPDATE",
            "timestamp": now_str,
            "feature_collection": {
                "type": "FeatureCollection",
                "features": polygon_features,
            },
        }, ["dashboard", "responders", "citizens"])

        # 3. Simulate Occasional Emergency SOS Bursts
        if self.step_count % 3 == 0:
            target_zone = random.choice(HINDON_YAMUNA_BASIN_POLYGONS)
            base_coord = target_zone["coordinates"][0]
            sos_event = {
                "event_type": "NEW_SOS_ALERT",
                "id": f"sim-sos-{self.step_count}",
                "phone_number": f"+91-98765{random.randint(10000, 99999)}",
                "emergency_type": random.choice(EMERGENCY_TYPES),
                "lat": round(base_coord[1] + random.uniform(-0.005, 0.005), 4),
                "lng": round(base_coord[0] + random.uniform(-0.005, 0.005), 4),
                "rain_rate": round(25.0 + rise_offset * 10 + random.uniform(0, 15), 1),
                "risk_status": "HIGH" if rise_offset > 1.0 else "MEDIUM",
                "status": "PENDING",
                "timestamp": now_str,
            }
            await manager.broadcast_to_rooms(sos_event, ["dashboard", "responders"])

        # 4. Simulate Vehicle Telemetry Movement
        for vehicle in self.vehicles:
            # Advance slightly toward target
            vehicle["lat"] = round(vehicle["lat"] + (vehicle["target_lat"] - vehicle["lat"]) * 0.05 + random.uniform(-0.0002, 0.0002), 5)
            vehicle["lng"] = round(vehicle["lng"] + (vehicle["target_lng"] - vehicle["lng"]) * 0.05 + random.uniform(-0.0002, 0.0002), 5)

        await manager.broadcast_to_rooms({
            "event_type": "VEHICLE_TELEMETRY_UPDATE",
            "timestamp": now_str,
            "vehicles": self.vehicles,
        }, ["dashboard", "responders"])


# Global simulation instance
simulation_harness = FloodSimulationHarness()
