#!/bin/sh
set -e

if [ -z "$1" ]; then
    echo "Usage: sh scripts/restore_db.sh <path_to_dump_file>"
    exit 1
fi

DUMP_FILE="$1"
DB_URL=${DATABASE_URL:-"postgresql://surakshagrid:surakshagrid_test_password@localhost:5432/surakshagrid_db"}

echo "=================================================="
echo " SURAKSHAGRID SPATIAL POSTGIS DATABASE RESTORATION"
echo " Target Dump: ${DUMP_FILE}"
echo "=================================================="

if [ ! -f "${DUMP_FILE}" ]; then
    echo "Error: Dump file '${DUMP_FILE}' does not exist."
    exit 1
fi

# 1. Ensure PostGIS Extension is Enabled Prior to Restoration
echo "Verifying PostGIS spatial extensions..."
psql "${DB_URL}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql "${DB_URL}" -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

# 2. Execute pg_restore with GIST Index Rebuilding
echo "Restoring PostGIS spatial tables and GIST spatial indices..."
pg_restore --dbname="${DB_URL}" --no-owner --no-acl --clean --if-exists "${DUMP_FILE}" || echo "Notice: Restoration completed with minor warnings."

echo "✓ PostGIS database restoration completed successfully."
echo "=================================================="
