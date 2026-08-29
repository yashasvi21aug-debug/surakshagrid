import pytest
from app.simulation import FloodSimulationHarness, HINDON_YAMUNA_BASIN_POLYGONS, SAFE_SHELTERS


@pytest.mark.asyncio
async def test_simulation_harness_tick():
    harness = FloodSimulationHarness(interval=0.1)
    assert not harness.is_running
    assert len(HINDON_YAMUNA_BASIN_POLYGONS) > 0
    assert len(SAFE_SHELTERS) > 0

    await harness._emit_simulation_tick()
    assert harness.step_count == 0  # _emit_simulation_tick called directly


@pytest.mark.asyncio
async def test_simulation_start_stop():
    harness = FloodSimulationHarness(interval=0.1)
    await harness.start(duration_seconds=0.3)
    assert harness.is_running
    await harness.stop()
    assert not harness.is_running
