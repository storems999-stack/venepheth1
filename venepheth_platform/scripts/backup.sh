#!/usr/bin/env bash
# ==============================================================================
# Venepheth Academic Platform - Automated Production Backup Script
# Conforms to 3-2-1 Enterprise Backup Strategy (Section 34, vision.txt)
# Includes AES-256 encryption for all backup archives.
# ==============================================================================
set -euo pipefail

# Always run from the project root. Under cron (or any absolute-path
# invocation) the current directory is $HOME, where manage.py does not exist.
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

if [ -z "$ENCRYPTION_KEY" ]; then
    echo "ERROR: BACKUP_ENCRYPTION_KEY must be set for backup encryption."
    exit 1
fi

echo "=================================================="
echo " Starting Venepheth Platform Backup: $(date)"
echo " Backup Directory: ${BACKUP_DIR}"
echo " Retention: ${KEEP_DAYS} days"
echo " Encryption: AES-256 enabled"
echo "=================================================="

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Run Django backup command
python manage.py backup_platform --output-dir "${BACKUP_DIR}" --keep-days "${KEEP_DAYS}" --encrypt

echo "=================================================="
echo " Backup completed successfully: $(date)"
echo "=================================================="
