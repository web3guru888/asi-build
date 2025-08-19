# Kenny AGI Blockchain Audit Trail Dockerfile

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN addgroup --system --gid 1001 kenny && \
    adduser --system --uid 1001 --gid 1001 kenny

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=kenny:kenny . .

# Create necessary directories
RUN mkdir -p logs && \
    mkdir -p data && \
    chown -R kenny:kenny /app

# Switch to non-root user
USER kenny

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

USER root
RUN pip install --no-cache-dir -r requirements.txt
USER kenny

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Additional production optimizations
ENV PYTHONOPTIMIZE=1

# Use gunicorn for production
CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]