#!/bin/sh
set -e

echo "=================================================="
echo " SURAKSHAGRID SPATIAL POSTGIS DATABASE BACKUP"
echo "=================================================="

# 1. Parse Database Connection String
DB_URL=${DATABASE_URL:-"postgresql://surakshagrid:surakshagrid_test_password@localhost:5432/surakshagrid_db"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/backups"
BACKUP_FILE="${BACKUP_DIR}/surakshagrid_postgis_dump_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

echo "Creating compressed PostGIS database dump: ${BACKUP_FILE}"

# 2. Execute Spatial pg_dump (-Fc format preserves geometry & GIST index metadata)
pg_dump "${DB_URL}" -Fc --no-owner --no-acl --file="${BACKUP_FILE}"

echo "✓ PostGIS dump completed cleanly ($(du -h "${BACKUP_FILE}" | cut -f1))"

# 3. Optional S3 / Cloudflare R2 Cloud Storage Sync
if [ -n "${S3_BACKUP_BUCKET}" ] && command -v aws >/dev/null 2>&1; then
    echo "Uploading database backup to S3 bucket: s3://${S3_BACKUP_BUCKET}/"
    aws s3 cp "${BACKUP_FILE}" "s3://${S3_BACKUP_BUCKET}/surakshagrid_postgis_dump_${TIMESTAMP}.dump"
    echo "✓ S3 cloud backup sync complete."
else
    echo "Notice: S3_BACKUP_BUCKET not set or aws-cli missing. Backup retained locally at ${BACKUP_FILE}."
fi

echo "=================================================="
