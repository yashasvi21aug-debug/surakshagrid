FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt

COPY . .
RUN PYTHONPATH=/install/lib/python3.11/site-packages python -m ml.train_and_save

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /build /app

EXPOSE 8000

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
