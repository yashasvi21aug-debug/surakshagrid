from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_root_index_template_rendering(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "SURAKSHAGRID" in response.text
    assert "INCIDENT COMMAND" in response.text


@pytest.mark.asyncio
async def test_citizen_template_rendering(client):
    response = await client.get("/citizen")
    assert response.status_code == 200
    assert "Citizen Emergency Portal" in response.text
    assert "CRITICAL_TRAPPED" in response.text


@pytest.mark.asyncio
async def test_driver_template_rendering(client):
    response = await client.get("/driver")
    assert response.status_code == 200
    assert "NDRF FIELD UNIT #4" in response.text


@pytest.mark.asyncio
async def test_dashboard_template_rendering(client):
    response = await client.get("/dashboard")
    assert response.status_code == 200
    assert "Digital Twin EOC Dashboard" in response.text
