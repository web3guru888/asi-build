# ASI:BUILD Production Dockerfile
# Multi-stage build for optimized production deployment

# Stage 1: Build Environment
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Set metadata labels
LABEL maintainer="ASI:BUILD Team <contact@asi-build.ai>"
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.version=$VERSION
LABEL org.label-schema.name="ASI:BUILD"
LABEL org.label-schema.description="Production ASI:BUILD Superintelligence Framework"
LABEL org.label-schema.url="https://asi-build.ai"
LABEL org.label-schema.schema-version="1.0"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    cmake \
    git \
    curl \
    wget \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    liblapack-dev \
    libblas-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Create build directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt ./
COPY setup.py ./
COPY README.md ./

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Install additional AI/ML dependencies
RUN pip install --no-cache-dir \
    torch>=2.0.0 \
    torchvision \
    torchaudio \
    transformers>=4.30.0 \
    accelerate \
    datasets \
    tokenizers \
    sentencepiece \
    protobuf \
    onnx \
    onnxruntime \
    tensorboard \
    wandb \
    mlflow \
    optuna \
    ray[default] \
    dask[complete] \
    qiskit \
    cirq \
    pennylane \
    networkx \
    neo4j \
    redis \
    celery \
    flower \
    prometheus-client \
    psutil \
    uvloop \
    orjson \
    httpx \
    aiofiles \
    aiokafka

# Install quantum computing dependencies
RUN pip install --no-cache-dir \
    qiskit-aer \
    qiskit-ibmq-provider \
    qiskit-optimization \
    qiskit-machine-learning \
    pennylane-lightning \
    pennylane-qiskit

# Install consciousness and neuroscience libraries
RUN pip install --no-cache-dir \
    brian2 \
    nest-simulator \
    neuron \
    mne \
    nilearn \
    sklearn \
    scipy \
    sympy

# Copy source code
COPY . .

# Build the package
RUN pip install -e .

# Stage 2: Runtime Environment
FROM python:3.11-slim as runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    gnupg \
    lsb-release \
    procps \
    htop \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -g 1000 asiuser && \
    useradd -r -u 1000 -g asiuser -d /home/asiuser -s /bin/bash -c "ASI:BUILD User" asiuser && \
    mkdir -p /home/asiuser && \
    chown -R asiuser:asiuser /home/asiuser

# Set up application directories
RUN mkdir -p /app /var/log/asi_build /var/lib/asi_build /etc/asi_build && \
    chown -R asiuser:asiuser /app /var/log/asi_build /var/lib/asi_build /etc/asi_build

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=asiuser:asiuser . /app

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV ASI_BUILD_HOME=/app
ENV ASI_BUILD_LOG_DIR=/var/log/asi_build
ENV ASI_BUILD_DATA_DIR=/var/lib/asi_build
ENV ASI_BUILD_CONFIG_DIR=/etc/asi_build

# Configure Python optimizations
ENV PYTHONOPTIMIZE=1
ENV PYTHONHASHSEED=random

# Security settings
ENV PYTHONSAFEPATH=1

# Resource limits
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV NUMEXPR_NUM_THREADS=4

# Switch to non-root user
USER asiuser

# Create configuration file
RUN echo '{\
  "system": {\
    "max_startup_time": 300,\
    "safety_check_interval": 10,\
    "reality_lock_default": true,\
    "god_mode_default": false,\
    "human_oversight_default": true\
  },\
  "safety": {\
    "emergency_shutdown_timeout": 5,\
    "reality_manipulation_allowed": false,\
    "consciousness_transfer_allowed": false,\
    "god_mode_authorization_required": true\
  },\
  "resources": {\
    "max_memory_gb": 32,\
    "max_cpu_cores": 8,\
    "max_gpu_memory_gb": 16,\
    "disk_space_gb": 100\
  },\
  "monitoring": {\
    "metrics_enabled": true,\
    "health_checks_enabled": true,\
    "dashboard_enabled": true\
  }\
}' > /etc/asi_build/config.json

# Health check script
RUN echo '#!/bin/bash\n\
curl -f http://localhost:8000/health || exit 1\n\
python -c "import psutil; exit(1 if psutil.virtual_memory().percent > 90 else 0)"\n\
python -c "import psutil; exit(1 if psutil.cpu_percent() > 95 else 0)"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Expose ports
EXPOSE 8000 8001 8080 9090 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Volume mounts for data persistence
VOLUME ["/var/log/asi_build", "/var/lib/asi_build", "/etc/asi_build"]

# Default command
CMD ["python", "-m", "asi_build_launcher"]

# Alternative entrypoints
# CMD ["python", "-m", "asi_build_api"] # For API-only mode
# CMD ["python", "-m", "monitoring"] # For monitoring-only mode

# Security: Run with read-only root filesystem
# Add --read-only flag when running container
# docker run --read-only --tmpfs /tmp --tmpfs /var/run asi-build:latest

# Production deployment command:
# docker run -d \
#   --name asi-build-prod \
#   --restart unless-stopped \
#   --read-only \
#   --tmpfs /tmp \
#   --tmpfs /var/run \
#   -p 8000:8000 \
#   -p 8001:8001 \
#   -p 8080:8080 \
#   -p 9090:9090 \
#   -p 3000:3000 \
#   -v asi_build_logs:/var/log/asi_build \
#   -v asi_build_data:/var/lib/asi_build \
#   -v asi_build_config:/etc/asi_build \
#   -e ASI_BUILD_MODE=production \
#   -e ASI_BUILD_SAFETY_LEVEL=maximum \
#   -e ASI_BUILD_REALITY_LOCKED=true \
#   --memory=32g \
#   --cpus=8 \
#   --security-opt=no-new-privileges:true \
#   --cap-drop=ALL \
#   --cap-add=NET_BIND_SERVICE \
#   asi-build:latest