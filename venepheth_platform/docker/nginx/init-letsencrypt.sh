#!/bin/bash
# =============================================================================
# init-letsencrypt.sh — First-time SSL certificate setup using Certbot/Let's Encrypt
# =============================================================================
# USAGE: DOMAIN=yourdomain.com EMAIL=you@example.com bash docker/nginx/init-letsencrypt.sh
# Run this ONCE on a fresh server before starting the production stack.
#
# The script rewrites the YOUR_DOMAIN placeholder in docker/nginx/nginx.prod.conf
# so the certificate paths nginx looks for match the ones certbot writes.
# =============================================================================

set -euo pipefail

# Always operate from the project root so the relative compose file resolves,
# even when invoked by cron or from another directory.
cd "$(dirname "$0")/../.."
PROJECT_ROOT="$(pwd)"

# ─── CONFIGURE THESE ─────────────────────────────────────────────────────────
: "${DOMAIN:?Set DOMAIN, e.g. DOMAIN=example.com}"
: "${EMAIL:?Set EMAIL for Let's Encrypt alerts, e.g. EMAIL=admin@example.com}"
STAGING="${STAGING:-0}"
# ─────────────────────────────────────────────────────────────────────────────

NGINX_CONF="docker/nginx/nginx.prod.conf"
CERTBOT_DATA_PATH="./docker/certbot"

if ! grep -q "YOUR_DOMAIN" "$NGINX_CONF"; then
  echo "❌  $NGINX_CONF has no YOUR_DOMAIN placeholder left."
  echo "    It may already be configured for a domain. Check it before re-running."
  exit 1
fi

echo "==> [0/6] Pointing nginx at $DOMAIN ..."
cp "$NGINX_CONF" "$NGINX_CONF.bak"
# The placeholder also appears in server_name, so this fixes both the cert
# paths and the vhost name in one pass.
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" "$NGINX_CONF"
if grep -q "YOUR_DOMAIN" "$NGINX_CONF"; then
  echo "❌  Failed to substitute the domain into $NGINX_CONF — aborting."
  mv "$NGINX_CONF.bak" "$NGINX_CONF"
  exit 1
fi
echo "    nginx now expects certificates in $CERTBOT_DATA_PATH/conf/live/$DOMAIN"

echo "==> [1/6] Creating dummy certificate for $DOMAIN..."
mkdir -p "$CERTBOT_DATA_PATH/conf/live/$DOMAIN"
docker compose -f docker-compose.prod.yml run --rm --entrypoint \
  "openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
    -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
    -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
    -subj '/CN=localhost'" certbot

echo "==> [2/6] Starting Nginx with dummy cert..."
docker compose -f docker-compose.prod.yml up --force-recreate -d nginx

echo "==> [3/6] Deleting dummy certificate..."
docker compose -f docker-compose.prod.yml run --rm --entrypoint \
  "rm -rf /etc/letsencrypt/live/$DOMAIN && \
   rm -rf /etc/letsencrypt/archive/$DOMAIN && \
   rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

echo "==> [4/6] Requesting real certificate from Let's Encrypt..."
STAGING_FLAG=""
if [ "$STAGING" -eq 1 ]; then
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

echo "==> [5/6] Reloading Nginx..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "==> [6/6] Verifying certificate files exist..."
for f in fullchain.pem privkey.pem; do
  if [ ! -f "$CERTBOT_DATA_PATH/conf/live/$DOMAIN/$f" ]; then
    echo "❌  Missing $CERTBOT_DATA_PATH/conf/live/$DOMAIN/$f — nginx will not start."
    exit 1
  fi
done

echo ""
echo "✅  SSL certificates for $DOMAIN are ready!"
echo "    Run: cd $PROJECT_ROOT && docker compose -f docker-compose.prod.yml up -d"
