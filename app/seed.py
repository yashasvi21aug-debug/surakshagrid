from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, SYNC_DATABASE_URL
from app.models.flood_zone import FloodZone, InundationZone
from app.models.gis_models import (
    CitizenSOS,
    CitizenStatus,
    EmergencyType,
    GaugeStatus,
    IoTWaterGauge,
    RescueUnit,
    RescueUnitStatus,
)
from app.models.spatial import Shelter
from app.models.user import User, UserRole

SHELTERS = [
    {"name": "Hindon High-Ground Relief Shelter", "lat": 28.6812, "lng": 77.3764, "capacity": 450},
    {"name": "Sahibabad Civil Defence Centre", "lat": 28.6765, "lng": 77.3516, "capacity": 300},
    {"name": "NCR East Evacuation School", "lat": 28.7148, "lng": 77.3182, "capacity": 600},
]

FLOOD_ZONES = [
    {
        "zone_name": "Hindon Basin North Lowland",
        "polygon": "POLYGON((77.3380 28.6620,77.3620 28.6620,77.3620 28.6850,77.3380 28.6850,77.3380 28.6620))",
        "water_depth_m": 1.45,
        "risk_level": "CRITICAL",
    },
    {
        "zone_name": "Hindon Basin South Floodplain",
        "polygon": "POLYGON((77.3650 28.6260,77.3890 28.6260,77.3890 28.6500,77.3650 28.6500,77.3650 28.6260))",
        "water_depth_m": 0.85,
        "risk_level": "HIGH",
    },
    {
        "zone_name": "Hindon Canal East Perimeter",
        "polygon": "POLYGON((77.3970 28.6960,77.4210 28.6960,77.4210 28.7180,77.3970 28.7180,77.3970 28.6960))",
        "water_depth_m": 0.42,
        "risk_level": "HIGH",
    },
]

GAUGES = [
    {
        "sensor_name": "Hindon-01",
        "lat": 28.6745,
        "lng": 77.3642,
        "current_water_level_m": 2.8,
        "warning_threshold_m": 2.5,
        "status": GaugeStatus.WARNING,
        "last_ping": datetime.now(timezone.utc),
    },
    {
        "sensor_name": "Yamuna-Delta-02",
        "lat": 28.6475,
        "lng": 77.2387,
        "current_water_level_m": 4.1,
        "warning_threshold_m": 3.2,
        "status": GaugeStatus.CRITICAL,
        "last_ping": datetime.now(timezone.utc) - timedelta(minutes=2),
    },
    {
        "sensor_name": "NCR-West-07",
        "lat": 28.5931,
        "lng": 77.1634,
        "current_water_level_m": 1.9,
        "warning_threshold_m": 2.3,
        "status": GaugeStatus.NORMAL,
        "last_ping": datetime.now(timezone.utc) - timedelta(minutes=8),
    },
    {
        "sensor_name": "East-Canal-11",
        "lat": 28.7140,
        "lng": 77.2965,
        "current_water_level_m": 3.4,
        "warning_threshold_m": 2.8,
        "status": GaugeStatus.WARNING,
        "last_ping": datetime.now(timezone.utc) - timedelta(minutes=5),
    },
]

INUNDATION_ZONES = [
    {
        "zone_name": "Yamuna-Right-Bank",
        "polygon": "POLYGON((77.2200 28.6200, 77.2320 28.6200, 77.2320 28.6400, 77.2200 28.6400, 77.2200 28.6200))",
        "risk_score": 0.85,
        "estimated_water_rise": 1.8,
        "predicted_horizon_hours": 6,
    },
    {
        "zone_name": "Hindon-Lowland",
        "polygon": "POLYGON((77.3380 28.6620, 77.3620 28.6620, 77.3620 28.6850, 77.3380 28.6850, 77.3380 28.6620))",
        "risk_score": 0.85,
        "estimated_water_rise": 1.8,
        "predicted_horizon_hours": 8,
    },
    {
        "zone_name": "NCR-East-Floodplain",
        "polygon": "POLYGON((77.3020 28.7060, 77.3220 28.7060, 77.3220 28.7350, 77.3020 28.7350, 77.3020 28.7060))",
        "risk_score": 0.85,
        "estimated_water_rise": 1.8,
        "predicted_horizon_hours": 10,
    },
]

RESCUE_UNITS = [
    {
        "unit_name": "NDRF Boat 01",
        "lat": 28.6590,
        "lng": 77.2490,
        "assigned_sos_id": None,
        "status": RescueUnitStatus.EN_ROUTE,
    },
    {
        "unit_name": "Rescue Truck 04",
        "lat": 28.6860,
        "lng": 77.3015,
        "assigned_sos_id": None,
        "status": RescueUnitStatus.STANDBY,
    },
]

USERS = [
    {"name": "Commander Rajesh Sharma", "phone_number": "+91-9876500001", "role": UserRole.ADMIN, "lat": 28.6321, "lng": 77.4446},
    {"name": "Rescue Pilot Vikas Verma", "phone_number": "+91-9876500002", "role": UserRole.RESPONDER, "lat": 28.6590, "lng": 77.2490},
    {"name": "Citizen Aarav Gupta", "phone_number": "+91-9876543210", "role": UserRole.CITIZEN, "lat": 28.6270, "lng": 77.2190},
]

SOS_RECORDS = [
    {
        "phone_number": "+91-9876543210",
        "emergency_type": EmergencyType.CRITICAL_TRAPPED,
        "lat": 28.6270,
        "lng": 77.2190,
        "rain_rate": 42.8,
        "risk_status": "HIGH",
        "status": CitizenStatus.PENDING,
        "timestamp": datetime.now(timezone.utc) - timedelta(minutes=12),
    },
    {
        "phone_number": "+91-9811122233",
        "emergency_type": EmergencyType.MEDICAL_EVAC,
        "lat": 28.6550,
        "lng": 77.2485,
        "rain_rate": 28.5,
        "risk_status": "MEDIUM",
        "status": CitizenStatus.DISPATCHED,
        "timestamp": datetime.now(timezone.utc) - timedelta(minutes=7),
    },
    {
        "phone_number": "+91-9000999911",
        "emergency_type": EmergencyType.CRITICAL_TRAPPED,
        "lat": 28.6940,
        "lng": 77.3045,
        "rain_rate": 58.4,
        "risk_status": "CRITICAL",
        "status": CitizenStatus.PENDING,
        "timestamp": datetime.now(timezone.utc) - timedelta(minutes=3),
    },
    {
        "phone_number": "+91-9765432100",
        "emergency_type": EmergencyType.MEDICAL_EVAC,
        "lat": 28.6810,
        "lng": 77.1820,
        "rain_rate": 19.2,
        "risk_status": "LOW",
        "status": CitizenStatus.RESOLVED,
        "timestamp": datetime.now(timezone.utc) - timedelta(minutes=20),
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


async def seed_users(session: AsyncSession) -> None:
    for u in USERS:
        existing = (await session.execute(select(User).where(User.phone_number == u["phone_number"]))).scalar_one_or_none()
        if existing is None:
            session.add(User(**u))


async def seed_gauges(session: AsyncSession) -> None:
    for gauge in GAUGES:
        existing = (await session.execute(select(IoTWaterGauge).where(IoTWaterGauge.sensor_name == gauge["sensor_name"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                IoTWaterGauge(
                    sensor_name=gauge["sensor_name"],
                    location=point_wkt(gauge["lat"], gauge["lng"]),
                    current_water_level_m=gauge["current_water_level_m"],
                    warning_threshold_m=gauge["warning_threshold_m"],
                    status=gauge["status"],
                    last_ping=gauge["last_ping"],
                )
            )


async def seed_inundation_zones(session: AsyncSession) -> None:
    for zone in INUNDATION_ZONES:
        existing = (await session.execute(select(InundationZone).where(InundationZone.zone_name == zone["zone_name"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                InundationZone(
                    zone_name=zone["zone_name"],
                    polygon=polygon_wkt(zone["polygon"]),
                    polygon_geojson=zone["polygon"],
                    risk_score=zone["risk_score"],
                    water_depth_m=zone["estimated_water_rise"],
                    estimated_water_rise=zone["estimated_water_rise"],
                    predicted_horizon_hours=zone["predicted_horizon_hours"],
                    created_at=datetime.now(timezone.utc),
                )
            )


async def seed_rescue_units(session: AsyncSession) -> None:
    for unit in RESCUE_UNITS:
        existing = (await session.execute(select(RescueUnit).where(RescueUnit.unit_name == unit["unit_name"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                RescueUnit(
                    unit_name=unit["unit_name"],
                    current_location=point_wkt(unit["lat"], unit["lng"]),
                    assigned_sos_id=unit["assigned_sos_id"],
                    status=unit["status"],
                )
            )


async def seed_sos_records(session: AsyncSession) -> None:
    for record in SOS_RECORDS:
        existing = (await session.execute(select(CitizenSOS).where(CitizenSOS.phone_number == record["phone_number"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                CitizenSOS(
                    phone_number=record["phone_number"],
                    emergency_type=record["emergency_type"],
                    location=point_wkt(record["lat"], record["lng"]),
                    lat=record["lat"],
                    lng=record["lng"],
                    rain_rate=record["rain_rate"],
                    risk_status=record["risk_status"],
                    status=record["status"],
                    timestamp=record["timestamp"],
                )
            )


async def seed_shelters(session: AsyncSession) -> None:
    for item in SHELTERS:
        existing = (await session.execute(select(Shelter).where(Shelter.name == item["name"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                Shelter(
                    name=item["name"],
                    geom=point_wkt(item["lat"], item["lng"]),
                    capacity=item["capacity"],
                    is_active=True,
                )
            )


async def seed_flood_zones(session: AsyncSession) -> None:
    for item in FLOOD_ZONES:
        existing = (await session.execute(select(FloodZone).where(FloodZone.zone_name == item["zone_name"]))).scalar_one_or_none()
        if existing is None:
            session.add(
                FloodZone(
                    zone_name=item["zone_name"],
                    polygon=polygon_wkt(item["polygon"]),
                    polygon_geojson=item["polygon"],
                    risk_score=0.85,
                    water_depth_m=item["water_depth_m"],
                    estimated_water_rise=item["water_depth_m"],
                    predicted_horizon_hours=6,
                )
            )


async def clear_demo_data(session: AsyncSession) -> None:
    for model_cls in (CitizenSOS, InundationZone, IoTWaterGauge, RescueUnit, Shelter, User):
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
        await seed_users(session)
        await seed_gauges(session)
        await seed_inundation_zones(session)
        await seed_rescue_units(session)
        await seed_sos_records(session)
        await seed_shelters(session)
        await seed_flood_zones(session)
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for SurakshaGrid")
    parser.add_argument("--keep-existing", action="store_true", help="Merge demo records without clearing existing ones")
    args = parser.parse_args()

    asyncio.run(seed_all(clear_existing=not args.keep_existing))
    print("SurakshaGrid demo data seeded successfully.")


if __name__ == "__main__":
    main()
