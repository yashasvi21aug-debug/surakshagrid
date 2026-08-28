from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
CLASSIFIER_MODEL = PROJECT_ROOT / "ml" / "models" / "inundation_classifier.json"
REGRESSOR_MODEL = PROJECT_ROOT / "ml" / "models" / "water_rise_regressor.json"
FALLBACK_INSTRUCTIONS = """
Fallback instructions:
  1. Copy .env.example to .env and verify DATABASE_URL.
  2. Start PostgreSQL/PostGIS with: docker compose up -d db
  3. Install dependencies in Python 3.11: python -m pip install -r requirements.txt
  4. Re-run this launcher: python run_local.py
""".strip()


def verify_environment() -> None:
    from app.config import settings

    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    if settings.DATABASE_URL.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL must point to PostgreSQL/PostGIS for local launch")
    print(f"Database target configured: {settings.DATABASE_URL.split('@')[-1]}")


def print_database_failure(error: Exception) -> None:
    print("\nSurakshaGrid could not reach PostgreSQL/PostGIS.")
    print(f"Database error: {error}")
    print(FALLBACK_INSTRUCTIONS)


def compile_model_artifacts() -> None:
    if CLASSIFIER_MODEL.is_file() and REGRESSOR_MODEL.is_file():
        print("Model artifacts found; skipping compilation.")
        return

    print("Model artifacts missing; compiling XGBoost weights...")
    subprocess.run(
        [sys.executable, "-m", "ml.train_and_save"],
        cwd=PROJECT_ROOT,
        check=True,
        env=os.environ.copy(),
    )


async def verify_database() -> None:
    from sqlalchemy import text

    from app.database import engine

    async with engine.connect() as connection:
        await connection.execute(text("SELECT PostGIS_Version()"))


async def initialize_database() -> None:
    from app.database import init_db

    await init_db()


async def database_is_empty() -> bool:
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models.gis_models import IoTWaterGauge
    from app.models.spatial import FloodZone, Shelter

    async with AsyncSessionLocal() as session:
        counts = [
            await session.scalar(select(func.count()).select_from(Shelter)),
            await session.scalar(select(func.count()).select_from(FloodZone)),
            await session.scalar(select(func.count()).select_from(IoTWaterGauge)),
        ]
    return all(count == 0 for count in counts)


def run_seed_script() -> None:
    seed_script = PROJECT_ROOT / "seed.py"
    if not seed_script.is_file():
        raise FileNotFoundError(f"Seeder script not found: {seed_script}")

    subprocess.run(
        [sys.executable, str(seed_script)],
        cwd=PROJECT_ROOT,
        check=True,
        env=os.environ.copy(),
    )


def run_server() -> int:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
    ]
    print("\nStarting Uvicorn at http://localhost:8000")
    print("Press Ctrl+C to stop the development server.\n")

    process = subprocess.Popen(command, cwd=PROJECT_ROOT, env=os.environ.copy())
    try:
        return process.wait()
    except KeyboardInterrupt:
        print("\nStopping Uvicorn...")
        process.terminate()
        try:
            return process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            return process.wait()


def main() -> int:
    os.chdir(PROJECT_ROOT)
    print("SurakshaGrid local launcher")
    print(f"Using configuration from: {PROJECT_ROOT / '.env'}")

    try:
        verify_environment()
        compile_model_artifacts()
    except KeyboardInterrupt:
        print("\nLauncher cancelled.")
        return 130
    except Exception as error:
        print("\nSurakshaGrid could not compile the ML model artifacts.")
        print(f"Model compilation error: {error}")
        print("Install the ML dependencies with: python -m pip install -r requirements.txt")
        print("Then retry: python run_local.py")
        return 1

    try:
        asyncio.run(verify_database())
        print("PostgreSQL/PostGIS connection verified.")
        asyncio.run(initialize_database())
        print("Database tables initialized.")
        if asyncio.run(database_is_empty()):
            run_seed_script()
            print("Demo data seeded into empty tables.")
        else:
            print("Existing data found; skipping demo seeder.")
    except KeyboardInterrupt:
        print("\nLauncher cancelled.")
        return 130
    except Exception as error:
        print_database_failure(error)
        return 1

    return run_server()


if __name__ == "__main__":
    raise SystemExit(main())
