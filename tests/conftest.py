from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.database import get_async_db, get_db
from app.main import app
from app.models.incident import CitizenSOS, CitizenStatus, EmergencyType
from app.schemas import FloodRiskResponse


class FakeResult:
    def __init__(self, records: list[Any]) -> None:
        self.records = records

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[Any]:
        return self.records

    def first(self) -> Any:
        return self.records[0] if self.records else None


class FakeAsyncSession:
    """Async database session mock for API integration tests."""

    def __init__(self) -> None:
        self.records: list[Any] = []
        self.zones: list[Any] = []
        self.gauges: list[Any] = []
        self.sos: list[Any] = []
        self.scalar_values: list[Any] = []

    def add(self, record: Any) -> None:
        if getattr(record, "id", None) is None:
            record.id = str(uuid.uuid4())
        if getattr(record, "timestamp", None) is None:
            record.timestamp = datetime.now(timezone.utc)
        self.records.append(record)
        if record.__class__.__name__ in ("CitizenSOS", "SOSIncident", "Incident") and record not in self.sos:
            self.sos.append(record)

    async def commit(self) -> None:
        return None

    async def refresh(self, record: Any) -> None:
        return None

    async def get(self, model: Any, record_id: str) -> Any:
        return next((item for item in self.records if str(item.id) == str(record_id)), None)

    async def execute(self, statement: Any) -> FakeResult:
        statement_text = str(statement).lower()
        if "inundation_zone" in statement_text or "flood_zone" in statement_text:
            return FakeResult(self.zones)
        if "iot_water_gauge" in statement_text:
            return FakeResult(self.gauges)
        if "count" in statement_text:
            return FakeResult([len(self.sos)])
        return FakeResult(self.sos)

    async def scalar(self, statement: Any) -> Any:
        if self.scalar_values:
            return self.scalar_values.pop(0)
        statement_text = str(statement).lower()
        if "count" in statement_text:
            return len(self.sos)
        if "st_asgeojson" in statement_text:
            return '{"type": "Polygon", "coordinates": [[[77.22, 28.62], [77.23, 28.62], [77.23, 28.64], [77.22, 28.64], [77.22, 28.62]]]}'
        if "st_x" in statement_text:
            return 77.2190
        if "st_y" in statement_text:
            return 28.6270
        return None


@pytest.fixture
def fake_db() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture
def mock_ml_service() -> MagicMock:
    mock_service = MagicMock()
    mock_service.predict_risk.return_value = FloodRiskResponse(
        inundation_probability=0.85,
        estimated_rise_time_hours=2.5,
        severity_classification="HIGH",
        is_fallback_mode=False,
    )
    return mock_service


@pytest.fixture
def mock_osrm_client() -> AsyncMock:
    mock_client = AsyncMock()
    mock_client.get_route.return_value = {
        "code": "Ok",
        "routes": [
            {
                "distance": 4200.0,
                "duration": 540.0,
                "geometry": {
                    "coordinates": [[77.2190, 28.6270], [77.2340, 28.6380], [77.2485, 28.6550]],
                    "type": "LineString",
                },
            }
        ],
    }
    return mock_client


@pytest_asyncio.fixture
async def client(fake_db: FakeAsyncSession):
    async def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_zone():
    def factory(**overrides: Any) -> Any:
        values = {
            "id": str(uuid.uuid4()),
            "zone_name": "Yamuna Critical Sector",
            "polygon": object(),
            "polygon_geojson": '{"type": "Polygon", "coordinates": [[[77.22, 28.62], [77.23, 28.62], [77.23, 28.64], [77.22, 28.64], [77.22, 28.62]]]}',
            "risk_score": 0.9,
            "estimated_water_rise": 1.8,
            "predicted_horizon_hours": 6,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    return factory


@pytest.fixture
def make_incident():
    def factory(**overrides: Any) -> Any:
        values = {
            "id": str(uuid.uuid4()),
            "phone_number": "+919876543210",
            "emergency_type": EmergencyType.CRITICAL_TRAPPED,
            "status": CitizenStatus.PENDING,
            "location": object(),
            "lat": 28.6270,
            "lng": 77.2190,
            "rain_rate": 12.0,
            "risk_status": "LOW",
            "timestamp": datetime.now(timezone.utc),
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    return factory
