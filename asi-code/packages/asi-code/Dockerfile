# ASI-Code Production Dockerfile
# Multi-stage build for optimized production image

# Build stage
FROM oven/bun:1.1.34-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json bun.lockb* ./

# Install dependencies
RUN bun install --frozen-lockfile --production=false

# Copy source code
COPY . .

# Build the application
RUN bun run build

# Production stage
FROM oven/bun:1.1.34-alpine AS production

# Install security updates and required packages
RUN apk update && apk upgrade && \
    apk add --no-cache \
    ca-certificates \
    curl \
    dumb-init \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 -S asicode && \
    adduser -S asicode -u 1001 -G asicode

# Set working directory
WORKDIR /app

# Copy built application from builder stage
COPY --from=builder --chown=asicode:asicode /app/dist ./dist
COPY --from=builder --chown=asicode:asicode /app/bin ./bin
COPY --from=builder --chown=asicode:asicode /app/package.json ./
COPY --from=builder --chown=asicode:asicode /app/node_modules ./node_modules

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/cache /var/log/asi-code && \
    chown -R asicode:asicode /app /var/log/asi-code

# Switch to non-root user
USER asicode

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Set environment variables
ENV NODE_ENV=production
ENV ASI_CONFIG_PATH=/app/config/production.yml
ENV ASI_DATA_DIR=/app/data
ENV ASI_LOG_DIR=/app/logs

# Use dumb-init as entrypoint for proper signal handling
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Start the application
CMD ["bun", "run", "start"]