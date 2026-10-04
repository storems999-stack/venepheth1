#!/usr/bin/env bash
# ==============================================================================
# Venepheth Academic Platform - Disaster Recovery Restore Script
# Conforms to Disaster Recovery Architecture (Section 35, vision.txt)
#
# Run the restore inside the production Compose service so it uses the
# configured database network, encrypted backup key, and backups volume.
# ==============================================================================
set -euo pipefail

# Always run from the project root.
cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.prod.yml"
ARCHIVE="${1:-}"

if [ ! -f .env.prod ]; then
    echo "ERROR: .env.prod is required to restore the production database." >&2
    exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is required to run the production restore." >&2
    exit 1
fi

if [ -z "$ARCHIVE" ]; then
    ARCHIVE_ARGS=()
    echo "No archive specified; restore_platform will select the latest verified archive."
else
    ARCHIVE_ARGS=(--archive "$ARCHIVE")
fi

echo "=================================================="
echo " Starting Disaster Recovery Restore: $(date)"
echo " Archive: ${ARCHIVE:-latest in /app/backups}"
echo "=================================================="

docker compose --env-file .env.prod -f "$COMPOSE_FILE" run --rm --build web \
    python manage.py restore_platform "${ARCHIVE_ARGS[@]}" --confirm

echo "=================================================="
echo " Platform Restore Complete: $(date)"
echo "=================================================="
