#!/usr/bin/env bash
# ==============================================================================
# Venepheth Academic Platform - Disaster Recovery Restore Script
# Conforms to Disaster Recovery Architecture (Section 35, vision.txt)
# ==============================================================================
set -euo pipefail

ARCHIVE="${1:-}"

if [ -z "${ARCHIVE}" ]; then
    echo "Usage: $0 /path/to/backup_archive.tar.gz"
    echo "Example: $0 /app/backups/backup_venepheth_platform_20260922_150000.tar.gz"
    exit 1
fi

echo "=================================================="
echo " Starting Disaster Recovery Restore: $(date)"
echo " Archive: ${ARCHIVE}"
echo "=================================================="

# Run Django restore command with confirmation
python manage.py restore_platform --archive "${ARCHIVE}" --confirm

echo "=================================================="
echo " Platform Restore Complete: $(date)"
echo "=================================================="
