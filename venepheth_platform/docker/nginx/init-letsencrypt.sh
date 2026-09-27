#!/bin/bash
# =============================================================================
# init-letsencrypt.sh — First-time SSL certificate setup using Certbot/Let's Encrypt
# =============================================================================
# USAGE: bash docker/nginx/init-letsencrypt.sh
# Run this ONCE on a fresh server before starting the production stack.
# =============================================================================

set -euo pipefail

# ─── CONFIGURE THESE ─────────────────────────────────────────────────────────
DOMAIN="yourdomain.com"
EMAIL="admin@yourdomain.com"       # Your real email for Let's Encrypt alerts
STAGING=0                          # Set to 1 for testing (avoids rate limits)
# ─────────────────────────────────────────────────────────────────────────────

CERTBOT_DATA_PATH="./docker/certbot"

echo "==> [1/5] Creating dummy certificate for $DOMAIN..."
mkdir -p "$CERTBOT_DATA_PATH/conf/live/$DOMAIN"
docker compose -f docker-compose.prod.yml run --rm --entrypoint \
  "openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
    -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
    -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
    -subj '/CN=localhost'" certbot

echo "==> [2/5] Starting Nginx with dummy cert..."
docker compose -f docker-compose.prod.yml up --force-recreate -d nginx

echo "==> [3/5] Deleting dummy certificate..."
docker compose -f docker-compose.prod.yml run --rm --entrypoint \
  "rm -rf /etc/letsencrypt/live/$DOMAIN && \
   rm -rf /etc/letsencrypt/archive/$DOMAIN && \
   rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

echo "==> [4/5] Requesting real certificate from Let's Encrypt..."
STAGING_FLAG=""
if [ $STAGING -eq 1 ]; then
    STAGING_FLAG="--staging"
    echo "    ⚠️  STAGING mode enabled."
fi

docker compose -f docker-compose.prod.yml run --rm --entrypoint \
  "certbot certonly --webroot --webroot-path=/var/www/certbot \
    $STAGING_FLAG \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN -d www.$DOMAIN" certbot

echo "==> [5/5] Reloading Nginx..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo ""
echo "✅  SSL certificates for $DOMAIN are ready!"
echo "    Run: docker compose -f docker-compose.prod.yml up -d"
