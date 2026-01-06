# Genesis AGI Framework - Docker Image

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including OpenCV requirements)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY README.md ./
COPY genesis ./genesis
COPY alembic ./alembic
COPY alembic.ini ./

# Install Genesis and dependencies
RUN pip install --no-cache-dir -e .

# Create data directories
RUN mkdir -p /data/.genesis/minds /data/.genesis/logs /data/chroma

# Environment variables
ENV GENESIS_HOME=/data/.genesis
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command: start API server
CMD ["genesis", "server", "--host", "0.0.0.0", "--port", "8000"]
