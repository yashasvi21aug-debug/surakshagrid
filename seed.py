from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from geoalchemy2 import WKTElement
from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models.gis_models import GaugeStatus, IoTWaterGauge
from app.models.spatial import FloodZone, Shelter


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

TELEMETRY_SENSORS = [
    {"sensor_name": "Hindon-Basin-01", "lat": 28.6745, "lng": 77.3642, "level": 2.8, "threshold": 2.5, "status": GaugeStatus.WARNING},
    {"sensor_name": "Hindon-Basin-02", "lat": 28.6475, "lng": 77.3787, "level": 3.6, "threshold": 3.0, "status": GaugeStatus.CRITICAL},
    {"sensor_name": "Hindon-East-03", "lat": 28.7140, "lng": 77.3965, "level": 2.1, "threshold": 2.4, "status": GaugeStatus.NORMAL},
    {"sensor_name": "Hindon-Canal-04", "lat": 28.6930, "lng": 77.4140, "level": 3.2, "threshold": 2.8, "status": GaugeStatus.WARNING},
]


def point_wkt(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def polygon_wkt(value: str) -> WKTElement:
    return WKTElement(value, srid=4326)


async def seed_shelters(session) -> int:
    existing = set((await session.execute(select(Shelter.name))).scalars().all())
    records = [
        Shelter(
            name=item["name"],
            geom=point_wkt(item["lat"], item["lng"]),
            capacity=item["capacity"],
            is_active=True,
        )
        for item in SHELTERS
        if item["name"] not in existing
    ]
    session.add_all(records)
    return len(records)


async def seed_flood_zones(session) -> int:
    existing = set((await session.execute(select(FloodZone.zone_name))).scalars().all())
    records = [
        FloodZone(
            zone_name=item["zone_name"],
            geom=polygon_wkt(item["polygon"]),
            water_depth_m=item["water_depth_m"],
            risk_level=item["risk_level"],
        )
        for item in FLOOD_ZONES
        if item["zone_name"] not in existing
    ]
    session.add_all(records)
    return len(records)


async def seed_telemetry(session) -> int:
    existing = set((await session.execute(select(IoTWaterGauge.sensor_name))).scalars().all())
    records = [
        IoTWaterGauge(
            sensor_name=item["sensor_name"],
            location=point_wkt(item["lat"], item["lng"]),
            current_water_level_m=item["level"],
            warning_threshold_m=item["threshold"],
            status=item["status"],
            last_ping=datetime.now(timezone.utc),
        )
        for item in TELEMETRY_SENSORS
        if item["sensor_name"] not in existing
    ]
    session.add_all(records)
    return len(records)


async def seed_all() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        counts = {
            "shelters": await seed_shelters(session),
            "flood_zones": await seed_flood_zones(session),
            "telemetry_sensors": await seed_telemetry(session),
        }
        await session.commit()
    return counts


def main() -> None:
    counts = asyncio.run(seed_all())
    print(
        "Seed complete: "
        f"{counts['shelters']} shelters, "
        f"{counts['flood_zones']} flood zones, "
        f"{counts['telemetry_sensors']} telemetry sensors."
    )

if __name__ == "__main__":
    main()
