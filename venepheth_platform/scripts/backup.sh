#!/usr/bin/env bash
# ==============================================================================
# Run an encrypted off-site backup from the Docker Compose production host.
# ==============================================================================
set -euo pipefail

# Always run from the project root. Under cron (or any absolute-path
# invocation) the current directory is $HOME, where manage.py does not exist.
cd "$(dirname "$0")/.."

KEEP_DAYS="${KEEP_DAYS:-14}"

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is required to run the production backup." >&2
    exit 1
fi
if [ ! -f .env.prod ]; then
    echo "ERROR: .env.prod is required for production backup credentials." >&2
    exit 1
fi

docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm web \
    python manage.py backup_platform \
    --output-dir /app/backups \
    --keep-days "${KEEP_DAYS}" \
    --encrypt \
    --upload
