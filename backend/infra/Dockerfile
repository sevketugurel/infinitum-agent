##############  Builder  ##############
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# sys deps only for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy just requirements first to leverage cache
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --no-compile -r requirements.txt

##############  Runtime  ##############
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/app/src

# only the shared libs we KNOW we need
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget libnss3 libatk-bridge2.0-0 libgtk-3-0 libdrm2 libxcb-dri3-0 && \
    rm -rf /var/lib/apt/lists/*

# non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# copy deps & app
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src ./src
COPY pyproject.toml README.md 

# optional Playwright (adds ~280 MB)
ARG INSTALL_PLAYWRIGHT=false
RUN if [ "$INSTALL_PLAYWRIGHT" = "true" ]; then \
        python -m playwright install --with-deps chromium; \
    fi

# Create necessary directories for CrewAI and other services
RUN mkdir -p /app/logs && \
    mkdir -p /home/appuser/.local/share && \
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT}/healthz || exit 1

EXPOSE ${PORT}
CMD ["uvicorn", "infinitum.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
