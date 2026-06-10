# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gruha Alankara — Production Dockerfile
# Multi-stage build: deps → app
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Stage 1: Dependencies
FROM python:3.11-slim AS deps

WORKDIR /build

# System deps for OpenCV, Pillow, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Application
FROM python:3.11-slim AS app

WORKDIR /app

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from deps stage
COPY --from=deps /install /usr/local

# Create non-root user
RUN groupadd -r gruha && useradd -r -g gruha -d /app -s /sbin/nologin gruha

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/chromadb /app/logs \
    && chown -R gruha:gruha /app

# Copy application code
COPY --chown=gruha:gruha . .

# Switch to non-root user
USER gruha

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Default command: Gunicorn with 4 workers
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
