from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def cmd_run(args: argparse.Namespace) -> int:
    """Initialize environment, verify database, seed demo data, and launch Uvicorn."""
    os.chdir(PROJECT_ROOT)
    print("==================================================")
    print(" SURAKSHAGRID INCIDENT COMMAND & DIGITAL TWIN CLI")
    print("==================================================")

    # 1. Compile ML Model Weights if missing
    classifier_path = PROJECT_ROOT / "ml" / "models" / "inundation_classifier.json"
    regressor_path = PROJECT_ROOT / "ml" / "models" / "water_rise_regressor.json"
    if not (classifier_path.is_file() and regressor_path.is_file()):
        print("ML model artifacts missing. Compiling XGBoost weights...")
        from ml.train_and_save import compile_models
        compile_models()
        print("ML model compilation complete.")
    else:
        print("XGBoost model weights verified.")

    # 2. Verify Database Connection & Initialize Tables
    print("Verifying database schema initialization...")
    try:
        from app.database import init_db
        asyncio.run(init_db())
        print("Database schema verified.")
    except Exception as error:
        print(f"Warning: Database initialization deferred (Mock Mode active): {error}")

    # 3. Seed Database if Empty
    if not args.no_seed:
        try:
            from app.database import AsyncSessionLocal
            from app.models.spatial import Shelter
            from sqlalchemy import func, select

            async def check_empty() -> bool:
                async with AsyncSessionLocal() as session:
                    count = await session.scalar(select(func.count()).select_from(Shelter))
                    return count == 0

            if asyncio.run(check_empty()):
                print("Database is empty. Seeding initial demo records...")
                from app.seed import seed_all
                asyncio.run(seed_all(clear_existing=False))
                print("Demo data seeded.")
        except Exception as error:
            print(f"Notice: Skipping seeder check ({error})")

    # 4. Launch Uvicorn Server
    print(f"\nStarting Uvicorn server at http://{args.host}:{args.port}")
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        command.append("--reload")

    process = subprocess.Popen(command, cwd=PROJECT_ROOT, env=os.environ.copy())
    try:
        return process.wait()
    except KeyboardInterrupt:
        print("\nStopping SurakshaGrid server...")
        process.terminate()
        try:
            return process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            return process.wait()


def cmd_seed(args: argparse.Namespace) -> int:
    """Seed demo data into PostgreSQL/PostGIS database."""
    print("Seeding SurakshaGrid database...")
    from app.seed import seed_all
    asyncio.run(seed_all(clear_existing=not args.keep_existing))
    print("SurakshaGrid demo data seeded successfully.")
    return 0


def cmd_train_ml(args: argparse.Namespace) -> int:
    """Train and persist XGBoost inundation classifier and regressor model weights."""
    print("Training XGBoost ML models...")
    from ml.train_and_save import compile_models
    results = compile_models()
    print(f"ML Models compiled: AUC = {results.get('classifier_auc', 'N/A')}, RMSE = {results.get('regressor_rmse', 'N/A')}")
    return 0


def cmd_process_sar(args: argparse.Namespace) -> int:
    """Process single-band Sentinel-1 SAR GeoTIFF and ingest inundation polygons into PostGIS."""
    if not args.input:
        print("Error: --input argument is required for SAR processing.")
        return 1
    print(f"Processing SAR raster: {args.input}...")
    from app.services.sar import process_sar_tif, ingest_flood_polygons_to_db
    result = process_sar_tif(args.input, threshold_db=args.threshold_db)
    print(f"Extracted {len(result.polygons)} water polygon(s). Total surface water area: {result.total_surface_water_area_sq_km} sq km")
    count = asyncio.run(ingest_flood_polygons_to_db(result.polygons))
    print(f"Persisted {count} inundation zone(s) into database.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app",
        description="SurakshaGrid Unified Incident Command & Digital Twin CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Launch SurakshaGrid development server")
    run_parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    run_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    run_parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")
    run_parser.add_argument("--no-seed", action="store_true", help="Skip automatic DB seeding check")

    # Command: seed
    seed_parser = subparsers.add_parser("seed", help="Seed demo records into database")
    seed_parser.add_argument("--keep-existing", action="store_true", help="Do not clear existing database records")

    # Command: train / train-ml
    subparsers.add_parser("train", help="Train and save ML model pipeline artifacts")
    subparsers.add_parser("train-ml", help="Train and save ML model pipeline artifacts")

    # Command: process-sar
    sar_parser = subparsers.add_parser("process-sar", help="Process Sentinel-1 SAR GeoTIFF")
    sar_parser.add_argument("--input", required=True, help="Path to SAR GeoTIFF file")
    sar_parser.add_argument("--threshold-db", type=float, default=-14.0, help="Backscatter threshold in dB")

    # Parse args (default to "run" if no subcommand specified)
    parsed_args = parser.parse_args(argv)
    if not parsed_args.command:
        parsed_args = parser.parse_args(["run", *(argv or [])])

    handlers = {
        "run": cmd_run,
        "seed": cmd_seed,
        "train": cmd_train_ml,
        "train-ml": cmd_train_ml,
        "process-sar": cmd_process_sar,
    }

    handler = handlers.get(parsed_args.command)
    if handler:
        return handler(parsed_args)
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
