# Multi-stage production Dockerfile
FROM python:3.12-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    HF_HUB_OFFLINE=0 \
    ANONYMIZED_TELEMETRY=False

# Working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Copy application source code
COPY . .

# Expose server port
EXPOSE 10000


# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/health', timeout=5)" 
# Start production server
CMD ["sh", "-c", "gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-10000}"]
