# Disaster Recovery Plan — Venepheth SAYAVONG Academic Platform

**Version:** 1.0  
**Date:** 2026-09-28  
**Owner:** Platform Administrator

---

## 1. Overview

This document defines the recovery procedures for the Venepheth Academic Platform in the event of a failure. It covers RTO/RPO targets, backup strategy, recovery steps, and incident procedures.

---

## 2. Recovery Objectives

| Metric | Target | Description |
|--------|--------|-------------|
| **RPO** (Recovery Point Objective) | ≤ 24 hours | Maximum acceptable data loss |
| **RTO** (Recovery Time Objective) | ≤ 4 hours | Maximum acceptable downtime |

---

## 3. Backup Strategy (3-2-1 Rule)

| Copy | Location | Frequency | Retention |
|------|----------|-----------|-----------|
| 1st  | Production PostgreSQL volume | Continuous | Server lifecycle |
| 2nd  | Local Docker backup volume | Daily encrypted archive | 14 days |
| 3rd  | Private Cloudflare R2 bucket, off-site (requires account/bucket credentials) | Daily encrypted archive + checksum | 365 days |

> The database and local backup volume are on the same host/storage failure
> domain. For strict 3-2-1 compliance, add a second local copy on a separate
> device or host; the off-site bucket alone does not provide two local media.

> ✅ **Encryption (implemented):** `backup_platform --encrypt` produces a Fernet
> (AES-128-CBC + HMAC-SHA256) `.tar.gz.enc` archive, and the `.sha256` sidecar
> hashes the **encrypted** bytes, so `restore_platform` verifies integrity
> *before* decrypting. `scripts/backup.sh` passes `--encrypt` and refuses to run
> unless `BACKUP_ENCRYPTION_KEY` is set.
>
> 🔑 **Key custody (do this before the first backup):**
> ```bash
> python manage.py generate_backup_key          # prints a key
> python manage.py generate_backup_key --write  # also writes backup_key.bin (0600)
> ```
> The key is **never auto-generated** by a backup run — a key silently minted
> inside a container disappears with that container and orphans every archive.
> Put the value in `BACKUP_ENCRYPTION_KEY` in `.env.prod`, and keep a printed
> copy **offline and separate from the backups**. Without it, encrypted archives
> are unrecoverable.
>
> ⚠️ **Not provisioned by this repository:** create the private R2 bucket and a
> bucket-scoped API token, then populate `S3_BACKUP_BUCKET`,
> `S3_BACKUP_PREFIX=venepheth/production`,
> `S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com`,
> `AWS_DEFAULT_REGION=auto`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`
> in `.env.prod`. Apply the repository policy
> [`deploy/r2-backup-lifecycle-365d.json`](./deploy/r2-backup-lifecycle-365d.json)
> to that dedicated bucket; it expires objects under the production prefix
> after 365 days. Applying this file replaces the bucket's lifecycle rules, so
> do not use it on a shared bucket without merging its existing rules first.
> Cloudflare documents lifecycle setup via Dashboard, Wrangler, and S3 API in
> [R2 object lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/).
> The repository cannot create the bucket/token or confirm live bucket policy.
> Monitor the daily Celery backup task and verify archive and checksum objects
> appear remotely.

### What is Backed Up

- **PostgreSQL database** — `pg_dump` compressed
- **Media files** — `/app/media/` (uploaded files, images)
- **Configuration** — `docker-compose.prod.yml`, Nginx config, and (separately, encrypted)
  the production `.env` — never the backup archive itself
- **SSL certificates** — Let's Encrypt certs
- **Backup encryption key** — offline only, never inside a backup archive

### Backup Scripts

```bash
# Daily backup (run on the Docker Compose host at 02:00).
0 2 * * * cd /srv/venepheth && ./scripts/backup.sh >> /var/log/backup.log 2>&1

# Monthly verification should use an archive downloaded from the remote bucket
# and run in a non-production restore environment.
```

`scripts/backup.sh` runs the encrypted backup command in the production web image.
The scheduled Celery backup uses the same encryption and upload path. Configure
For Cloudflare R2, set `S3_BACKUP_BUCKET`, `S3_BACKUP_PREFIX`,
`S3_ENDPOINT_URL`, `AWS_DEFAULT_REGION=auto`, and the R2
`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in `.env.prod`. The backup command
fails explicitly if the bucket is missing or either upload fails; check Celery
logs and the bucket after setup. The local archive retention is 14 days; the
R2 lifecycle rule independently retains remote archives and checksums for 365
days.

For a restore drill, download both the archive and its matching `.sha256` object
from the bucket, then run `restore_platform --verify-only --archive <path>` in
a disposable restore environment. To restore data, follow the procedures below
only after validating the archive, key, target database, and media destination.

`scripts/restore.sh` runs the restore in the production web container, so it
uses the Compose database network, `.env.prod` encryption key, and `backups_vol`.
Place any off-site archive and its `.sha256` file in that volume under
`/app/backups/`, then run with no argument to select the latest archive or pass
its container path:

```bash
./scripts/restore.sh
./scripts/restore.sh /app/backups/backup_venepheth_platform_<ts>.tar.gz.enc
```

The PostgreSQL dump is restored as a single transaction; a failed SQL statement
rolls back the restore rather than leaving a partially replaced database. Media
files are restored from the same archive.

> ⚠️ **CRITICAL**: Test restore at least once per month. A backup that has never been tested is not a backup.

---

## 4. Failure Scenarios & Recovery Procedures

### 4.1 Application Crash (Django/Gunicorn down)

**Symptoms:** HTTP 502/503, container not running  
**RTO target:** < 5 minutes

```bash
# Check container status
docker compose -f docker-compose.prod.yml ps

# Restart application
docker compose -f docker-compose.prod.yml restart web

# Check logs
docker compose -f docker-compose.prod.yml logs web --tail=100
```

---

### 4.2 Database Failure

**Symptoms:** Django 500 errors mentioning DB connection, health check fails  
**RTO target:** < 1 hour

```bash
# Check PostgreSQL status
docker compose -f docker-compose.prod.yml ps db
docker compose -f docker-compose.prod.yml logs db --tail=50

# Restart DB
docker compose -f docker-compose.prod.yml restart db

# If data is corrupt — restore from backup (accepts plain or .enc archives)
BACKUP_ENCRYPTION_KEY=... ./scripts/restore.sh /app/backups/backup_venepheth_platform_<ts>.tar.gz.enc
```

---

### 4.3 Full Server Loss

**Symptoms:** Server unreachable, all services down  
**RTO target:** < 4 hours

**Recovery Steps:**

```
Step 1: Provision new server (Linux, same or equivalent specs)
Step 2: Install Docker + Docker Compose
Step 3: Clone repository from GitHub
Step 4: Restore .env.prod and BACKUP_ENCRYPTION_KEY from the offline secret store
Step 5: Place the verified archive and .sha256 sidecar in the Compose backups volume
Step 6: Run ./scripts/restore.sh (restores PostgreSQL and media from the archive)
Step 7: docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
Step 8: Verify health check: curl https://yourdomain.com/health/
Step 9: Update DNS if server IP changed
Step 10: Verify SSL certificate (Let's Encrypt or Cloudflare)
```

Detailed restore command:
```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm --build web \
  python manage.py restore_platform \
  --archive /app/backups/backup_venepheth_platform_<ts>.tar.gz.enc --confirm
```

---

### 4.4 Security Incident (Unauthorized Access)

**Immediate Actions (within 1 hour):**

1. **Isolate** — Block suspicious IP in Cloudflare/firewall
2. **Rotate secrets** — Regenerate `SECRET_KEY`, DB passwords, tokens
3. **Revoke sessions** — Run: `python manage.py clearsessions`
4. **Audit** — Review `AuditLog`, `SecurityEvent`, and access logs
5. **Notify** — Inform platform owner and affected parties if data was exposed
6. **Document** — Record timeline, actions taken, and root cause

```bash
# Emergency: force all users to re-login
python manage.py shell -c "
from django.contrib.sessions.models import Session
Session.objects.all().delete()
print('All sessions cleared.')
"
```

---

### 4.5 Data Corruption

**Symptoms:** Unexpected data in database, content missing  
**Steps:**

1. Identify the time of corruption from audit logs
2. Restore from a backup taken before the corruption
3. Apply data selectively if possible (avoid full restore if only partial data is affected)
4. Use `simple_history` to review and revert individual record changes

---

## 5. Emergency Admin Access

If the primary admin account is locked:

1. Access the server directly via SSH
2. Run Django shell with superuser:
   ```bash
   docker compose -f docker-compose.prod.yml run --rm web \
     python manage.py createsuperuser --email recovery@venepheth.edu.la
   ```
3. Log into `/admin/` with the recovery account
4. Investigate and restore the original admin account

---

## 6. Communication Plan

| Event | Who to Notify | Method |
|-------|--------------|--------|
| Planned maintenance | Users (if any) | Email / Site banner |
| Unplanned downtime < 1h | Platform owner | Direct message |
| Downtime > 1h | Platform owner + stakeholders | Email |
| Security incident | Platform owner + affected parties | Email + direct |

---

## 7. Recovery Test Schedule

| Test | Frequency | Last Tested |
|------|-----------|-------------|
| Backup restore (dry-run) | Monthly | — |
| Full DR drill (new server) | Quarterly | — |
| Security incident response | Semi-annually | — |

---

## 8. Contact Information

| Role | Responsibility |
|------|---------------|
| Platform Owner | Venepheth SAYAVONG |
| System Administrator | (fill in) |
| Database Administrator | (fill in) |

---

> **Last Updated:** 2026-09-28  
> **Review Due:** 2027-03-28
