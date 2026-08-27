from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.gis_models import CitizenStatus


class FakeResult:
    def __init__(self, records: list[Any]) -> None:
        self.records = records

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[Any]:
        return self.records


class FakeAsyncSession:
    """Small async session double for API tests that do not need a live PostGIS server."""

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
        if record.__class__.__name__ == "CitizenSOS" and record not in self.sos:
            self.sos.append(record)

    async def commit(self) -> None:
        return None

    async def refresh(self, record: Any) -> None:
        return None

    async def get(self, model: Any, record_id: str) -> Any:
        return next((item for item in self.records if item.id == record_id), None)

    async def execute(self, statement: Any) -> FakeResult:
        statement_text = str(statement).lower()
        if "inundation_zone" in statement_text:
            return FakeResult(self.zones)
        if "iot_water_gauge" in statement_text:
            return FakeResult(self.gauges)
        return FakeResult(self.sos)

    async def scalar(self, statement: Any) -> Any:
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None


@pytest.fixture
def fake_db() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture
def sqlite_test_url() -> str:
    return os.getenv("TEST_SQLITE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture
def postgis_test_url() -> str:
    return os.getenv("TEST_POSTGIS_URL", settings.DATABASE_URL)


@pytest_asyncio.fixture
async def client(fake_db: FakeAsyncSession):
    async def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
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
            "emergency_type": SimpleNamespace(value="CRITICAL_TRAPPED"),
            "status": CitizenStatus.PENDING,
            "location": object(),
            "rain_rate": 12.0,
            "risk_status": "LOW",
            "timestamp": datetime.now(timezone.utc),
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    return factory
