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

# pg_dump/pg_restore may be newer than the PostgreSQL server. restore_platform
# removes only the PG17-only default transaction_timeout setting when restoring
# to an older server, then applies the generated SQL in one rollback-safe
# transaction.

# Create non-root user for security
RUN groupadd --system venepheth && \
    useradd --system --gid venepheth --home /home/venepheth \
    --create-home venepheth

WORKDIR /app

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY . .

# Create necessary directories
RUN mkdir -p logs media staticfiles backups && \
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
