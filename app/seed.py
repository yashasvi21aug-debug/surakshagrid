from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, SYNC_DATABASE_URL
from app.models import (
    CitizenSOS,
    CitizenStatus,
    EmergencyType,
    FloodZone,
    GaugeStatus,
    Incident,
    InundationZone,
    IoTWaterGauge,
    Officer,
    OfficerRole,
    RescueUnit,
    RescueUnitStatus,
    SensorTelemetry,
    Shelter,
    User,
    UserRole,
)
from app.services.auth import hash_password

# 1. Synthetic PostGIS Flood Zones (3 Multi-polygon extents across urban river basins)
FLOOD_ZONES_SEED = [
    {
        "zone_name": "Hindon River Basin North Lowland",
        "source": "SAR",
        "risk_level": "CRITICAL",
        "depth_m": 2.8,
        "polygon": "POLYGON((77.3380 28.6620, 77.3620 28.6620, 77.3620 28.6850, 77.3380 28.6850, 77.3380 28.6620))",
    },
    {
        "zone_name": "Hindon Basin South Floodplain",
        "source": "ML",
        "risk_level": "HIGH",
        "depth_m": 1.45,
        "polygon": "POLYGON((77.3650 28.6260, 77.3890 28.6260, 77.3890 28.6500, 77.3650 28.6500, 77.3650 28.6260))",
    },
    {
        "zone_name": "Yamuna East Perimeter Canal Sector",
        "source": "ML",
        "risk_level": "MODERATE",
        "depth_m": 0.65,
        "polygon": "POLYGON((77.2200 28.6200, 77.2450 28.6200, 77.2450 28.6450, 77.2200 28.6450, 77.2200 28.6200))",
    },
]

# 2. IoT River Sensors (5 Monitoring stations with real-time gauges & safe thresholds)
SENSORS_SEED = [
    {
        "sensor_id": "SENSOR-HD-01",
        "name": "Hindon Barrage Gauge 01",
        "water_level_m": 3.85,
        "threshold_m": 2.50,
        "lat": 28.6745,
        "lng": 77.3642,
    },
    {
        "sensor_id": "SENSOR-YM-02",
        "name": "Yamuna Bridge Delta Gauge 02",
        "water_level_m": 4.10,
        "threshold_m": 3.20,
        "lat": 28.6475,
        "lng": 77.2387,
    },
    {
        "sensor_id": "SENSOR-NW-07",
        "name": "NCR West Stream Gauge 07",
        "water_level_m": 1.85,
        "threshold_m": 2.30,
        "lat": 28.5931,
        "lng": 77.1634,
    },
    {
        "sensor_id": "SENSOR-EC-11",
        "name": "East Canal Regulating Gate 11",
        "water_level_m": 3.40,
        "threshold_m": 2.80,
        "lat": 28.7140,
        "lng": 77.2965,
    },
    {
        "sensor_id": "SENSOR-SB-05",
        "name": "Sahibabad Feeder Gauge 05",
        "water_level_m": 2.95,
        "threshold_m": 2.40,
        "lat": 28.6765,
        "lng": 77.3516,
    },
]

# 3. Incidents / Citizen SOS Markers (10 Priority Distress Requests)
INCIDENTS_SEED = [
    {"phone": "+91-9876543210", "category": "CRITICAL_TRAPPED", "lat": 28.6321, "lng": 77.4446, "notes": "Submerged residential ground floor. 4 citizens stranded on roof."},
    {"phone": "+91-9811122233", "category": "MEDICAL_EVAC", "lat": 28.6550, "lng": 77.2485, "notes": "Dialysis patient requires urgent boat medical evacuation."},
    {"phone": "+91-9000999911", "category": "FOOD_WATER", "lat": 28.6940, "lng": 77.3045, "notes": "Community shelter food ration supplies depleted for 25 people."},
    {"phone": "+91-9765432100", "category": "CRITICAL_TRAPPED", "lat": 28.6810, "lng": 77.3520, "notes": "Elderly couple trapped in flooded vehicle near bridge."},
    {"phone": "+91-9822334455", "category": "MEDICAL_EVAC", "lat": 28.6410, "lng": 77.3890, "notes": "Infant with high fever stranded in inundated sector."},
    {"phone": "+91-9833445566", "category": "FOOD_WATER", "lat": 28.6180, "lng": 77.4120, "notes": "Drinking water contamination. Emergency supply requested."},
    {"phone": "+91-9844556677", "category": "CRITICAL_TRAPPED", "lat": 28.6650, "lng": 77.3300, "notes": "Rising water level in basement apartment."},
    {"phone": "+91-9855667788", "category": "FOOD_WATER", "lat": 28.7020, "lng": 77.3150, "notes": "Relief camp infant formula and dry ration shortage."},
    {"phone": "+91-9866778899", "category": "MEDICAL_EVAC", "lat": 28.6290, "lng": 77.2650, "notes": "Injured field volunteer needing stretcher transfer."},
    {"phone": "+91-9877889900", "category": "CRITICAL_TRAPPED", "lat": 28.6720, "lng": 77.3780, "notes": "Flash flood overflow blocking evacuation exit."},
]

# 4. Command Officers (1 Commander, 2 Field Operators)
OFFICERS_SEED = [
    {
        "badge_id": "NDRF-3492",
        "name": "Commander Rajesh Sharma",
        "email": "commander.sharma@ndrf.gov.in",
        "role": OfficerRole.COMMANDER,
        "password": "Password123!",
    },
    {
        "badge_id": "NDRF-7701",
        "name": "Operator Vikas Verma",
        "email": "vikas.verma@ndrf.gov.in",
        "role": OfficerRole.FIELD_OPERATOR,
        "password": "Password123!",
    },
    {
        "badge_id": "NDRF-7702",
        "name": "Operator Priya Singh",
        "email": "priya.singh@ndrf.gov.in",
        "role": OfficerRole.FIELD_OPERATOR,
        "password": "Password123!",
    },
]


def point_wkt(lat: float, lng: float) -> Any:
    if SYNC_DATABASE_URL.startswith("sqlite"):
        return f"POINT({lng} {lat})"
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def polygon_wkt(polygon_text: str) -> Any:
    if SYNC_DATABASE_URL.startswith("sqlite"):
        return polygon_text
    return WKTElement(polygon_text, srid=4326)


async def seed_officers(session: AsyncSession) -> None:
    for item in OFFICERS_SEED:
        existing = (await session.execute(select(Officer).where(Officer.badge_id == item["badge_id"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                Officer(
                    badge_id=item["badge_id"],
                    name=item["name"],
                    email=item["email"],
                    role=item["role"],
                    hashed_password=hash_password(item["password"]),
                    is_active=True,
                )
            )


async def seed_sensors(session: AsyncSession) -> None:
    for item in SENSORS_SEED:
        existing = (await session.execute(select(SensorTelemetry).where(SensorTelemetry.sensor_id == item["sensor_id"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                SensorTelemetry(
                    sensor_id=item["sensor_id"],
                    name=item["name"],
                    water_level_m=item["water_level_m"],
                    threshold_m=item["threshold_m"],
                    location=point_wkt(item["lat"], item["lng"]),
                    timestamp=datetime.now(timezone.utc),
                )
            )

        # Mirror in legacy table for backward compatibility
        existing_gauge = (await session.execute(select(IoTWaterGauge).where(IoTWaterGauge.sensor_name == item["name"]))).scalar_one_or_none()
        if existing_gauge is None:
            session.add(
                IoTWaterGauge(
                    sensor_name=item["name"],
                    location=point_wkt(item["lat"], item["lng"]),
                    current_water_level_m=item["water_level_m"],
                    warning_threshold_m=item["threshold_m"],
                    status=GaugeStatus.CRITICAL if item["water_level_m"] > item["threshold_m"] else GaugeStatus.NORMAL,
                    last_ping=datetime.now(timezone.utc),
                )
            )


async def seed_flood_zones(session: AsyncSession) -> None:
    for item in FLOOD_ZONES_SEED:
        existing = (await session.execute(select(FloodZone).where(FloodZone.zone_name == item["zone_name"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                FloodZone(
                    zone_name=item["zone_name"],
                    source=item["source"],
                    risk_level=item["risk_level"],
                    depth_m=item["depth_m"],
                    water_depth_m=item["depth_m"],
                    polygon=polygon_wkt(item["polygon"]),
                    polygon_geojson=item["polygon"],
                    valid_until=datetime.now(timezone.utc) + timedelta(hours=12),
                )
            )


async def seed_incidents(session: AsyncSession) -> None:
    for i, item in enumerate(INCIDENTS_SEED):
        cat_enum = EmergencyType.CRITICAL_TRAPPED
        if item["category"] == "MEDICAL_EVAC":
            cat_enum = EmergencyType.MEDICAL_EVAC
        elif item["category"] == "FOOD_WATER":
            cat_enum = EmergencyType.FOOD_WATER

        existing = (await session.execute(select(Incident).where(Incident.notes == item["notes"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                Incident(
                    category=cat_enum,
                    status=CitizenStatus.PENDING if i % 2 == 0 else CitizenStatus.DISPATCHED,
                    location=point_wkt(item["lat"], item["lng"]),
                    accuracy=5.0,
                    notes=item["notes"],
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=i * 5),
                )
            )

        existing_sos = (await session.execute(select(CitizenSOS).where(CitizenSOS.phone_number == item["phone"]))).scalar_one_or_none()
        if existing_sos is None:
            session.add(
                CitizenSOS(
                    phone_number=item["phone"],
                    emergency_type=cat_enum,
                    location=point_wkt(item["lat"], item["lng"]),
                    lat=item["lat"],
                    lng=item["lng"],
                    rain_rate=45.0,
                    risk_status="HIGH",
                    status=CitizenStatus.PENDING if i % 2 == 0 else CitizenStatus.DISPATCHED,
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=i * 5),
                )
            )


async def clear_demo_data(session: AsyncSession) -> None:
    """Clear demo records prior to seeding."""
    for model_cls in (Incident, SensorTelemetry, Officer, FloodZone, CitizenSOS, IoTWaterGauge, User):
        try:
            await session.execute(model_cls.__table__.delete())
        except Exception:
            pass


async def seed_all(clear_existing: bool = True) -> None:
    from app.database import init_db_async
    await init_db_async()

    async with AsyncSessionLocal() as session:
        if clear_existing:
            await clear_demo_data(session)
        await seed_officers(session)
        await seed_sensors(session)
        await seed_flood_zones(session)
        await seed_incidents(session)
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic PostGIS demo data for SurakshaGrid EOC Dashboard")
    parser.add_argument("--keep-existing", action="store_true", help="Merge demo records without clearing existing ones")
    args = parser.parse_args()

    asyncio.run(seed_all(clear_existing=not args.keep_existing))
    print("✓ SurakshaGrid PostGIS demo data seeded successfully.")


if __name__ == "__main__":
    main()
