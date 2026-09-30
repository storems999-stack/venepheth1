# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-xlib-2.0-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/production.txt ./requirements/
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels \
    -r requirements/production.txt

# ─── Stage 2: Runner ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# NOTE: pg_dump/pg_restore should match the server major version. The distro
# package currently resolves to 17 while compose pins postgres:16, so archives
# carry `SET transaction_timeout = 0` (a PG17 GUC) that a PG16 server rejects.
# restore_platform classifies that specific "errors ignored on restore" exit as
# a warning because the dump is still fully applied — see
# _is_benign_pg_restore_exit(). Pinning postgresql-client-16 (PGDG repo) would
# remove the mismatch at the source; that is left as an operator decision
# because it adds an external apt repository.

# Create non-root user for security
RUN groupadd --system venepheth && \
    useradd --system --gid venepheth --home /home/venepheth \
    --create-home venepheth

WORKDIR /app

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY . .

# Create necessary directories
RUN mkdir -p logs media staticfiles && \
    chown -R venepheth:venepheth /app

# Switch to non-root user
USER venepheth

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "config.wsgi:application"]

# ─── Stage 3: Production (alias for docker-compose target) ───────────────────
FROM runner AS production
