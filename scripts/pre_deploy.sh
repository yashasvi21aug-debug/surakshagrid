#!/bin/sh
set -e

echo "=== SURAKSHAGRID PRE-DEPLOYMENT INIT ==="
echo "Executing database PostGIS setup and Alembic migrations..."

# Run Alembic migrations to apply latest SRID 4326 PostGIS schema
alembic upgrade head

echo "=== PRE-DEPLOYMENT INIT COMPLETED SUCCESSFULLY ==="
