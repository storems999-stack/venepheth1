# Windows Docker + Cloudflare Tunnel deployment

This runbook deploys the Django application to the production Compose stack on
the Windows Docker host and connects the existing Cloudflare Tunnel to it.
GitHub stores the source; the Windows computer remains the server and must stay
awake and online.

## Safety model

- The production Compose project is named `venepheth-production`, uses its own
  Docker network and named volumes, and does not reuse the development
  database/media volumes.
- The Nginx origin is published only on `127.0.0.1:8081`. Do not publish this
  port on a LAN/public interface or forward it from the router.
- Cloudflare terminates public HTTPS. Nginx talks to Django over the internal
  Docker network and tells Django the original request used HTTPS.
- Take and verify an encrypted backup before restoring or migrating data.
- Do not commit `.env.prod`, `backup_key.bin`, tunnel tokens, or backup files.

## 1. Prepare and protect configuration

Open PowerShell in the repository root (`venepheth_platform`), then check Docker:

```powershell
docker compose version
docker compose ps
```

Keep the existing development services running while preparing production. If
`.env.prod` does not exist, copy the template once:

```powershell
Copy-Item .env.prod.example .env.prod
```

Edit `.env.prod` locally. Set strong unique values for Django, PostgreSQL and
Redis. Confirm these settings match the real site:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
DOMAIN=venepheth.online
ALLOWED_HOSTS=venepheth.online,www.venepheth.online
CSRF_TRUSTED_ORIGINS=https://venepheth.online,https://www.venepheth.online
SECURE_SSL_REDIRECT=True
TUNNEL_ORIGIN_PORT=8081
TRUSTED_PROXY_IPS=172.29.0.2
```

`REDIS_URL` must use the same password as `REDIS_PASSWORD`; URL-encode reserved
characters in the URL password. The checked-in sample email username, password,
and sender are placeholders. Configure real SMTP credentials locally before
relying on password-reset, verification, or contact email features. Do not put
those credentials in chat or Git.

`BACKUP_ENCRYPTION_KEY` must be a valid Fernet key and must be the same key used
to encrypt any archive that will be restored. Keep a protected offline copy.
The checked-in template intentionally contains placeholders; never use those
placeholder values as production credentials. Do not replace an existing
encryption key if it protects backups you still need.

## 2. Create and verify a fresh backup

This captures the currently running development database and media. It writes
an encrypted archive under the ignored `backups` folder and does not stop or
modify the development containers:

```powershell
docker compose exec -T web python manage.py backup_platform `
  --output-dir /app/backups --keep-days 0 --encrypt
```

List archives by timestamp and verify the exact archive before proceeding:

```powershell
Get-ChildItem .\backups\backup_venepheth_platform_*.tar.gz.enc |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 Name,Length,LastWriteTime

docker compose exec -T web python manage.py restore_platform `
  --verify-only `
  --archive /app/backups/backup_venepheth_platform_<timestamp>.tar.gz.enc
```

The verify-only command checks the encrypted checksum, decryption key, manifest,
and database dump without restoring data. Stop here if verification fails.

## 3. Validate the isolated production configuration

The second Compose file changes only the production Nginx/TLS edge and assigns
the isolated project/network. Validate the merged config:

```powershell
docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml config --quiet
```

Start only production PostgreSQL and Redis first, then wait for them to report
healthy:

```powershell
docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml up -d db redis

docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml ps
```

At this point the development stack should still be running under
`venepheth_platform-*`; production containers and volumes should use
`venepheth-production-*`.

## 4. Initialize production and restore the verified snapshot

Build the production image, apply schema migrations, and collect static files:

```powershell
docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml build web celery celery-beat

docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml run --rm web `
  python manage.py migrate --noinput

docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml run --rm web `
  python manage.py collectstatic --noinput
```

Start only the production Django service. It has no host-published port; this
creates its isolated backup volume so the archive can be copied into it:

```powershell
docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml up -d web
```

Copy the verified archive from the host into the isolated production backup
volume. Replace `<timestamp>` with the exact file name verified above:

```powershell
$web = docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml ps -q web
docker cp .\backups\backup_venepheth_platform_<timestamp>.tar.gz.enc `
  "${web}:/app/backups/"
docker cp .\backups\backup_venepheth_platform_<timestamp>.tar.gz.enc.sha256 `
  "${web}:/app/backups/"
```

Verify the copied archive, then restore it into the new production database and
media volume. This overwrites the target production database; confirm that it
is the new isolated `venepheth-production` database before running `--confirm`.

```powershell
docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml exec -T web `
  python manage.py restore_platform --verify-only `
  --archive /app/backups/backup_venepheth_platform_<timestamp>.tar.gz.enc

docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml exec -T web `
  python manage.py restore_platform --confirm `
  --archive /app/backups/backup_venepheth_platform_<timestamp>.tar.gz.enc
```

After restore, run migrations again and collect static files again:

```powershell
docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml run --rm web `
  python manage.py migrate --noinput

docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml run --rm web `
  python manage.py collectstatic --noinput
```

## 5. Start and test the origin locally

```powershell
docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml up -d

docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml ps

Invoke-WebRequest http://127.0.0.1:8081/health/live/
```

The health endpoint should return HTTP 200 with `{"status":"alive"}`. Also test
the homepage, admin login, static files, protected downloads, and Celery health
locally before routing public traffic. The wrong-host request should be
rejected. Do not expose port 8081 to the LAN.

## 6. Connect the existing Cloudflare Tunnel

In Cloudflare Zero Trust → **Networking → Tunnels**, open the existing
`venepheth.online` tunnel and edit its published application route:

- Hostname: `venepheth.online`
- Service type: HTTP
- Service URL: `http://localhost:8081`

If using `www.venepheth.online`, add a separate DNS/Tunnel route for `www` and
keep it in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

Install the connector using the install command shown in the Cloudflare
Dashboard on this Windows host. Run it from an elevated Command Prompt or
PowerShell. Keep the tunnel token secret; do not paste it into chat or Git. If
`cloudflared` is installed as a Windows service, check it with:

```powershell
Get-Service cloudflared
```

The Tunnel dashboard should show the connector as healthy with at least one
active replica. Then test, in order:

```powershell
Invoke-WebRequest https://venepheth.online/health/live/
Invoke-WebRequest https://venepheth.online/
```

Only use the site after both requests reach the Django production service and
return the expected responses. The Cloudflare Worker is not in this direct
Tunnel path; do not point the Tunnel route back to the Worker.

## 7. Keep it available and recoverable

- Keep Windows awake while plugged in (run in PowerShell; `0` means never):

  ```powershell
  powercfg /change standby-timeout-ac 0
  ```

- Configure Docker Desktop to start with Windows and keep the production
  containers at `restart: unless-stopped`.
- Keep the `cloudflared` service set to start automatically.
- Keep the PC online; shutdown, reboot, network outage, or Docker Desktop exit
  makes the site unavailable.
- Back up production regularly, store an encrypted copy off the PC, and
  periodically verify restores.
- Monitor tunnel status, container health, disk space, and backup age.

## Rollback

If production checks fail before the public route is changed, stop only the new
production project; development remains untouched:

```powershell
docker compose --env-file .env.prod `
  -f docker-compose.prod.yml -f docker-compose.tunnel.yml down
```

Do not add `-v`; that preserves production volumes for diagnosis/retry. If the
public Tunnel route has already been changed, point it back to the previous
working origin while investigating.
