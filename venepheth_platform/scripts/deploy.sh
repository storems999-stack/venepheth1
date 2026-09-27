#!/bin/bash
# =============================================================================
# deploy.sh — Zero-downtime production deployment script
# =============================================================================
# USAGE:
#   bash scripts/deploy.sh
#
# PREREQUISITES:
#   - Docker & Docker Compose are installed on the server
#   - .env.prod file exists and is configured
#   - Docker Swarm is initialized: docker swarm init
# =============================================================================

set -euo pipefail

STACK_NAME="venepheth"
IMAGE_NAME="venepheth_platform:prod"
COMPOSE_FILE="docker-compose.prod.yml"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Venepheth Platform — Production Deployment               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ─── Step 1: Pull latest code ────────────────────────────────────────────────
echo "==> [1/6] Pulling latest code from git..."
git pull origin main

# ─── Step 2: Build the Docker image ─────────────────────────────────────────
echo "==> [2/6] Building Docker image: $IMAGE_NAME..."
docker build --target production -t "$IMAGE_NAME" .
echo "    ✓ Image built successfully."

# ─── Step 3: Run database migrations ────────────────────────────────────────
echo "==> [3/6] Running database migrations..."
docker run --rm --env-file .env.prod "$IMAGE_NAME" \
  python manage.py migrate --noinput
echo "    ✓ Migrations applied."

# ─── Step 4: Collect static files ───────────────────────────────────────────
echo "==> [4/6] Collecting static files..."
docker run --rm --env-file .env.prod \
  -v "$(pwd)/staticfiles:/app/staticfiles" \
  "$IMAGE_NAME" python manage.py collectstatic --noinput --clear
echo "    ✓ Static files collected."

# ─── Step 5: Deploy or update the stack ─────────────────────────────────────
echo "==> [5/6] Deploying stack '$STACK_NAME' to Docker Swarm..."
docker stack deploy \
  --compose-file "$COMPOSE_FILE" \
  --with-registry-auth \
  --prune \
  "$STACK_NAME"
echo "    ✓ Stack deployed."

# ─── Step 6: Health check ────────────────────────────────────────────────────
echo "==> [6/6] Waiting for health check..."
sleep 10
if curl -fsSL "http://localhost/health/" > /dev/null 2>&1; then
  echo "    ✅  Health check passed!"
else
  echo "    ⚠️  Health check failed. Please check logs:"
  echo "       docker service logs ${STACK_NAME}_web"
  exit 1
fi

echo ""
echo "✅  Deployment complete! Stack: $STACK_NAME"
echo "    View services: docker stack services $STACK_NAME"
echo "    View web logs: docker service logs -f ${STACK_NAME}_web"
