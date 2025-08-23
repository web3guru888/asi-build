#!/bin/bash
set -e

echo "Starting MLOps platform in development mode..."

# Create necessary directories
mkdir -p tmp/logs
mkdir -p models/registry
mkdir -p models/deployments

# Build the gateway
echo "Building API Gateway..."
cd cmd/gateway
go build -o ../../bin/gateway
cd ../..

# Build the model server
echo "Building Model Server..."
cd cmd/model-server
go build -o ../../bin/model-server
cd ../..

# Build the API service
echo "Building API Service..."
cd cmd/api
go build -o ../../bin/api
cd ../..

# Start services in background
echo "Starting services..."

# Start model server on port 8081
echo "Starting Model Server on port 8081..."
if ! ./bin/model-server --port=8081 --models-dir=models/deployments > tmp/logs/model-server.log 2>&1 & then
    echo "Failed to start model server"
    exit 1
fi
MODEL_SERVER_PID=$!

# Start API service on port 8082
echo "Starting API Service on port 8082..."
if ! ./bin/api --port=8082 --db-path=models/registry > tmp/logs/api.log 2>&1 & then
    echo "Failed to start api service"
    kill $MODEL_SERVER_PID 2>/dev/null || true
    exit 1
fi
API_PID=$!

# Start gateway on port 8080
echo "Starting API Gateway on port 8080..."
if ! ./bin/gateway --port=8080 --api-host=http://localhost:8082 --model-host=http://localhost:8081 > tmp/logs/gateway.log 2>&1 & then
    echo "Failed to start gateway"
    kill $MODEL_SERVER_PID $API_PID 2>/dev/null || true
    exit 1
fi
GATEWAY_PID=$!

# Create cleanup function
cleanup() {
    echo "Shutting down services..."
    kill $GATEWAY_PID $API_PID $MODEL_SERVER_PID 2>/dev/null || true
    wait $GATEWAY_PID $API_PID $MODEL_SERVER_PID 2>/dev/null || true
    echo "All services stopped."
    exit 0
}

# Trap termination signals
trap cleanup SIGINT SIGTERM

# Wait for termination signal
echo "MLOps platform running in development mode. Press Ctrl+C to stop."
echo "API Gateway: http://localhost:8080"
echo "API Service: http://localhost:8082"
echo "Model Server: http://localhost:8081"

# Monitor logs in real-time
tail -f tmp/logs/gateway.log tmp/logs/api.log tmp/logs/model-server.log &
TAIL_PID=$!

# Wait for signals
wait $TAIL_PID $GATEWAY_PID $API_PID $MODEL_SERVER_PID 2>/dev/null || true

cleanup