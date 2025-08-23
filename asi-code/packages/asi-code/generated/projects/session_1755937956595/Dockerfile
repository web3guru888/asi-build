FROM golang:1.22-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

# Build the API Gateway
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o cmd/gateway/gateway cmd/gateway/main.go

# Build the Model Server
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o cmd/model-server/server cmd/model-server/main.go

# Build the API Service
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o cmd/api/api cmd/api/main.go

# Create minimal runtime image for gateway
FROM alpine:latest AS gateway
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/cmd/gateway/gateway .
EXPOSE 8080
CMD ["./gateway"]

# Create minimal runtime image for model server
FROM alpine:latest AS model-server
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/cmd/model-server/server .
EXPOSE 9000
CMD ["./server"]

# Create minimal runtime image for API service
FROM alpine:latest AS api
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/cmd/api/api .
EXPOSE 8000
CMD ["./api"]

# Multi-stage targets for deployment flexibility
LABEL org.opencontainers.image.title="MLOps Platform" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.source="https://github.com/fetchai/mlops-platform" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.vendor="Fetch.ai" \
      com.fetchai.platform.role="mlops-platform"

# Default target is gateway (can be overridden during build)
ARG TARGETARCH
ARG TARGETOS
LABEL arch=${TARGETARCH} os=${TARGETOS}

# Final target - use gateway by default
# Build with: docker build --target gateway|model-server|api .
CMD ["./gateway"]