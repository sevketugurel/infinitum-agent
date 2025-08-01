# Multi-stage build for optimized production image
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (minimal for AI libraries)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set work directory
WORKDIR /app

# Copy requirements and install (use full requirements)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install minimal runtime dependencies 
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set work directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Install Playwright browsers for Crawl4AI (if available)
RUN python -m playwright install chromium || echo "Playwright installation skipped - will use fallback methods"

# Create a sample environment file for reference
RUN echo "# Environment variables for Docker container" > .env.sample && \
    echo "# Copy this to .env and fill in your values" >> .env.sample && \
    echo "GCP_PROJECT_ID=your-project-id" >> .env.sample && \
    echo "GOOGLE_API_KEY=your-google-api-key" >> .env.sample && \
    echo "GEMINI_API_KEY=your-gemini-api-key" >> .env.sample && \
    echo "SERPAPI_API_KEY=your-serpapi-key" >> .env.sample && \
    echo "FIREBASE_PROJECT_ID=your-project-id" >> .env.sample && \
    echo "ENVIRONMENT=production" >> .env.sample && \
    echo "" >> .env.sample && \
    echo "# Enhanced Logging Configuration" >> .env.sample && \
    echo "LOG_LEVEL=INFO" >> .env.sample && \
    echo "ENABLE_STRUCTURED_LOGGING=true" >> .env.sample && \
    echo "ENABLE_RICH_LOGGING=false" >> .env.sample && \
    echo "LOG_SAMPLING_RATE=1.0" >> .env.sample && \
    echo "ENABLE_METRICS=true" >> .env.sample && \
    echo "ENABLE_TRACING=true" >> .env.sample && \
    echo "ENABLE_PERFORMANCE_LOGGING=true" >> .env.sample && \
    echo "LOG_SLOW_OPERATIONS=true" >> .env.sample && \
    echo "SLOW_OPERATION_THRESHOLD=1.0" >> .env.sample && \
    echo "# SENTRY_DSN=your-sentry-dsn-for-error-tracking" >> .env.sample

# Create necessary directories and fix permissions
RUN mkdir -p /app/logs && \
    mkdir -p /home/appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/healthz || exit 1

# Expose port
EXPOSE $PORT

# Start command (use the real main application)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]