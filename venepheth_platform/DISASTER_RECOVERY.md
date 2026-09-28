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
| 1st  | Local server volume | Continuous (PostgreSQL WAL) | 7 days |
| 2nd  | Secondary server / external drive | Daily (pg_dump + media) | 30 days |
| 3rd  | Off-site (cloud / remote location) | Weekly encrypted archive | 90 days |

### What is Backed Up

- **PostgreSQL database** — `pg_dump` compressed
- **Media files** — `/app/media/` (uploaded files, images)
- **Configuration** — `.env` (encrypted), `docker-compose.prod.yml`, Nginx config
- **SSL certificates** — Let's Encrypt certs

### Backup Scripts

```bash
# Daily backup (run via cron at 02:00)
0 2 * * * /app/scripts/backup.sh >> /var/log/backup.log 2>&1

# Verify restore monthly
0 9 1 * * /app/scripts/restore.sh --dry-run >> /var/log/restore-test.log 2>&1
```

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

# If data is corrupt — restore from backup
./scripts/restore.sh --latest
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
Step 4: Restore .env file from encrypted backup
Step 5: Restore PostgreSQL from latest backup
Step 6: Restore media files
Step 7: docker compose -f docker-compose.prod.yml up -d
Step 8: Verify health check: curl https://yourdomain.com/health/
Step 9: Update DNS if server IP changed
Step 10: Verify SSL certificate (Let's Encrypt or Cloudflare)
```

Detailed restore command:
```bash
# Restore PostgreSQL
docker compose -f docker-compose.prod.yml run --rm db \
  psql -U venepheth_app venepheth_db < backup_YYYYMMDD.sql

# Restore media
rsync -avz /backup/media/ /app/media/
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
