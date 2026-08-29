# Multi-stage Dockerfile for SurakshaGrid Geospatial Backend on Render
# Stage 1: Build & Compile C-Extensions & Wheels
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt

COPY . .
RUN PYTHONPATH=/install/lib/python3.11/site-packages python -m ml.train_hydrology

# Stage 2: Lean Production Runtime Image
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        netcat-openbsd \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user for enhanced container security
RUN groupadd -g 10001 appgroup \
    && useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder --chown=appuser:appgroup /build /app

USER appuser

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
