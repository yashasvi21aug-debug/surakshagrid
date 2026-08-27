from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
FALLBACK_INSTRUCTIONS = """
Fallback instructions:
  1. Copy .env.example to .env and verify DATABASE_URL.
  2. Start PostgreSQL/PostGIS with: docker compose up -d db
  3. Install dependencies in Python 3.11: python -m pip install -r requirements.txt
  4. Re-run this launcher: python run_local.py
""".strip()


def print_database_failure(error: Exception) -> None:
    print("\nSurakshaGrid could not reach PostgreSQL/PostGIS.")
    print(f"Database error: {error}")
    print(FALLBACK_INSTRUCTIONS)


async def verify_database() -> None:
    from sqlalchemy import text

    from app.database import engine

    async with engine.connect() as connection:
        await connection.execute(text("SELECT PostGIS_Version()"))


async def initialize_database() -> None:
    from app.database import init_db

    await init_db()


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
        asyncio.run(verify_database())
        print("PostgreSQL/PostGIS connection verified.")
        asyncio.run(initialize_database())
        print("Database tables initialized.")
        run_seed_script()
        print("Demo data seeded.")
    except KeyboardInterrupt:
        print("\nLauncher cancelled.")
        return 130
    except Exception as error:
        print_database_failure(error)
        return 1

    return run_server()


if __name__ == "__main__":
    raise SystemExit(main())
