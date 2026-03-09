# ─── Stage 1: Dependency builder ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && pip install --no-cache-dir --prefix=/install gunicorn==23.0.0

# ─── Stage 2: Production runtime ─────────────────────────────────────────────
FROM python:3.12-slim AS final

LABEL org.opencontainers.image.source="https://github.com/asilbeek17/dreamzone-mock"
LABEL org.opencontainers.image.description="CDI Mock Test System — Dreamzone"

# Rootless execution: appuser UID 1000
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/sh -m appuser

# Runtime deps: libpq5 (postgres), gettext (compilemessages), curl (healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gettext \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application source (owned by appuser from the start)
COPY --chown=appuser:appuser . .

# Ensure writable data directories exist
RUN mkdir -p staticfiles media && \
    chown -R appuser:appuser staticfiles media

# Make entrypoint executable
RUN chmod +x scripts/entrypoint.sh

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

ENTRYPOINT ["scripts/entrypoint.sh"]