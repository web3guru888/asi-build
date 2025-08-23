#!/bin/bash
set -e

# Build production binaries for MLOps platform
echo "Building production binaries for MLOps platform..."

# Set build variables
BUILD_TIME=$(date -u '+%Y-%m-%d_%H:%M:%S')
VERSION="${VERSION:-$(git describe --tags --abbrev=0 2>/dev/null || echo 'v0.1.0')}"
COMMIT_HASH="${COMMIT_HASH:-$(git rev-parse HEAD 2>/dev/null | head -c8 || echo 'unknown')}"
BUILD_PLATFORM="linux/amd64"

# Create dist directory
rm -rf dist
mkdir -p dist/bin

# Build API service
echo "Building API service..."
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
  -ldflags "-X main.version=$VERSION -X main.commit=$COMMIT_HASH -X main.date=$BUILD_TIME -s -w" \
  -o dist/bin/api \
  cmd/api/main.go

# Build Gateway service
echo "Building Gateway service..."
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
  -ldflags "-X main.version=$VERSION -X main.commit=$COMMIT_HASH -X main.date=$BUILD_TIME -s -w" \
  -o dist/bin/gateway \
  cmd/gateway/main.go

# Build Model Server service
echo "Building Model Server service..."
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
  -ldflags "-X main.version=$VERSION -X main.commit=$COMMIT_HASH -X main.date=$BUILD_TIME -s -w" \
  -o dist/bin/model-server \
  cmd/model-server/main.go

# Copy configuration files
echo "Copying configuration files..."
mkdir -p dist/config
cp -r config/* dist/config/ 2>/dev/null || true

# Copy necessary assets
echo "Copying assets..."
mkdir -p dist/assets
cp -r public/* dist/assets/ 2>/dev/null || true

# Create release info file
cat > dist/RELEASE.txt << EOF
MLOps Platform Production Build
===============================
Version: $VERSION
Commit: $COMMIT_HASH
Built: $BUILD_TIME
Platform: $BUILD_PLATFORM

Binaries:
- api: MLOps core API service
- gateway: API Gateway and load balancer
- model-server: Model inference server

Instructions:
1. Deploy binaries to target machines
2. Ensure configuration is properly set in config/
3. Run each service with: ./binary --config=config/config.yaml

Environment Variables:
- LOG_LEVEL: debug, info, warn, error (default: info)
- ENV: development, production (default: production)

Ports:
- API: \${API_PORT:-8080}
- Gateway: \${GATEWAY_PORT:-8000}
- Model Server: \${MODEL_SERVER_PORT:-9000}

Monitoring:
- Metrics: /metrics (Prometheus)
- Health: /health
- Tracing: OpenTelemetry supported

Security:
- JWT authentication enforced
- Secure headers enabled
- Rate limiting applied

Built with ❤️ by ASI:One - Agentive MLOps Platform
EOF

# Set executable permissions
chmod +x dist/bin/*

# Generate checksums
echo "Generating checksums..."
cd dist && sha256sum bin/* > checksums.txt && cd ..

echo "Build completed successfully!"
echo "Artifacts created in ./dist"

# Verify binaries
echo "Verifying binaries..."
dist/bin/api --help > /dev/null 2>&1 && echo "✓ API binary verified"
dist/bin/gateway --help > /dev/null 2>&1 && echo "✓ Gateway binary verified"
dist/bin/model-server --help > /dev/null 2>&1 && echo "✓ Model Server binary verified"

echo "Build process finished. Ready for deployment."