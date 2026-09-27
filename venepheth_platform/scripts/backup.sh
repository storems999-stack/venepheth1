#!/usr/bin/env bash
# ==============================================================================
# Venepheth Academic Platform - Automated Production Backup Script
# Conforms to 3-2-1 Enterprise Backup Strategy (Section 34, vision.txt)
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"

echo "=================================================="
echo " Starting Venepheth Platform Backup: $(date)"
echo " Backup Directory: ${BACKUP_DIR}"
echo " Retention: ${KEEP_DAYS} days"
echo "=================================================="

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Run Django backup command
python manage.py backup_platform --output-dir "${BACKUP_DIR}" --keep-days "${KEEP_DAYS}"

echo "=================================================="
echo " Backup completed successfully: $(date)"
echo "=================================================="
