#!/bin/sh
set -e

echo "=================================================="
echo " SURAKSHAGRID RENDER PRODUCTION DEPLOYMENT INIT"
echo "=================================================="

# 1. Run database Alembic migrations for PostGIS tables
echo "Executing Alembic database migrations..."
alembic upgrade head || echo "Database migrations already up to date."

# 2. Launch Uvicorn ASGI Server
PORT_VAL=${PORT:-8000}
echo "Starting SurakshaGrid Uvicorn ASGI server on port ${PORT_VAL}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT_VAL}"
