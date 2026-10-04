#!/usr/bin/env bash
# Deploy the single-host production Docker Compose stack.
# Requires Docker Compose and a server-side .env.prod file.
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.prod.yml"

if [ ! -f .env.prod ]; then
    echo "ERROR: .env.prod is required for production deployment." >&2
    exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is required for production deployment." >&2
    exit 1
fi

compose() {
    docker compose --env-file .env.prod -f "$COMPOSE_FILE" "$@"
}

wait_for_healthy_service() {
    local service="$1"
    local container_id status attempt
    for attempt in $(seq 1 30); do
        container_id="$(compose ps -q "$service")"
        if [ -n "$container_id" ]; then
            status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$container_id")"
            case "$status" in
                healthy) return 0 ;;
                unhealthy)
                    echo "ERROR: $service failed its health check." >&2
                    compose logs --tail=100 "$service" >&2
                    return 1
                    ;;
            esac
        fi
        sleep 5
    done
    echo "ERROR: $service did not become healthy in time." >&2
    compose logs --tail=100 "$service" >&2
    return 1
}

echo "==> Pulling latest code from git..."
git pull --ff-only origin main

echo "==> Building production application image..."
compose build web celery celery-beat

echo "==> Starting database and Redis..."
compose up -d db redis
wait_for_healthy_service db
wait_for_healthy_service redis

echo "==> Applying database migrations..."
compose run --rm --no-deps web python manage.py migrate --noinput

echo "==> Collecting static files..."
compose run --rm --no-deps web python manage.py collectstatic --noinput

echo "==> Recreating application services (single-host Compose rollout)..."
compose up -d --no-deps --force-recreate web celery celery-beat
wait_for_healthy_service web
wait_for_healthy_service celery
compose up -d nginx certbot

echo "Deployment complete."
echo "Check services with: docker compose --env-file .env.prod -f $COMPOSE_FILE ps"
