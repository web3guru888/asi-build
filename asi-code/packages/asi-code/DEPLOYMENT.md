# ASI-Code Deployment Guide

This guide covers deployment options, configuration, and best practices for running ASI-Code in production environments.

## Table of Contents

- [Deployment Options](#deployment-options)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Configuration](#configuration)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployments](#cloud-deployments)
- [Load Balancing](#load-balancing)
- [Monitoring](#monitoring)
- [Security](#security)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Deployment Options

ASI-Code supports multiple deployment strategies:

1. **Standalone Server**: Single node deployment
2. **Docker Container**: Containerized deployment
3. **Kubernetes**: Scalable container orchestration
4. **Cloud Services**: Managed cloud deployments
5. **Edge Deployment**: Distributed edge computing

### Comparison Matrix

| Option | Complexity | Scalability | Management | Cost |
|--------|------------|-------------|------------|------|
| Standalone | Low | Limited | Manual | Low |
| Docker | Medium | Medium | Semi-automated | Medium |
| Kubernetes | High | High | Automated | Medium-High |
| Cloud Services | Medium | Very High | Managed | Variable |
| Edge | High | Distributed | Complex | High |

## Prerequisites

### System Requirements

**Minimum Requirements:**
- **CPU**: 2 cores, 2.4 GHz
- **RAM**: 4 GB
- **Storage**: 20 GB SSD
- **Network**: 10 Mbps bandwidth

**Recommended Requirements:**
- **CPU**: 4+ cores, 3.0+ GHz
- **RAM**: 8+ GB
- **Storage**: 100+ GB NVMe SSD
- **Network**: 100+ Mbps bandwidth

### Software Dependencies

- **Node.js**: Version 18.0.0 or higher
- **Bun**: Version 1.0.0 or higher (recommended)
- **Database**: PostgreSQL 13+ or MongoDB 4.4+ (optional)
- **Redis**: Version 6.0+ (for caching and sessions)
- **Reverse Proxy**: Nginx or Apache (recommended)

### Platform Support

- **Linux**: Ubuntu 20.04+, CentOS 8+, RHEL 8+
- **macOS**: 10.15+ (development only)
- **Windows**: Windows Server 2019+ (with WSL2)
- **Docker**: Any platform with Docker support
- **Cloud**: AWS, Azure, GCP, DigitalOcean

## Environment Setup

### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y curl wget git build-essential

# Install Node.js (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Bun
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc
```

### 2. User Setup

```bash
# Create dedicated user for ASI-Code
sudo useradd -m -s /bin/bash asi-code
sudo usermod -aG sudo asi-code

# Switch to ASI-Code user
sudo su - asi-code

# Create application directory
mkdir -p /home/asi-code/app
cd /home/asi-code/app
```

### 3. Application Installation

```bash
# Download and extract ASI-Code
wget https://github.com/asi-team/asi-code/releases/latest/download/asi-code.tar.gz
tar -xzf asi-code.tar.gz

# Install dependencies
cd asi-code
bun install --production

# Build application
bun run build

# Set permissions
chmod +x bin/asi-code.js
```

## Configuration

### 1. Environment Variables

Create a `.env` file with production settings:

```bash
# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key

# Server Configuration
NODE_ENV=production
PORT=3000
HOST=0.0.0.0

# Database (if using persistent storage)
DATABASE_URL=postgresql://user:password@localhost:5432/asicode
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET=your-super-secure-jwt-secret
ENCRYPTION_KEY=your-32-character-encryption-key

# Logging
LOG_LEVEL=info
LOG_FORMAT=json

# Performance
MAX_CONCURRENT_SESSIONS=100
CACHE_TTL=3600
```

### 2. Configuration File

Create `asi-code.config.yml`:

```yaml
# Production Configuration
server:
  port: 3000
  host: 0.0.0.0
  cors:
    enabled: true
    origins:
      - https://your-domain.com
  
providers:
  default:
    name: default
    type: anthropic
    apiKey: ${ANTHROPIC_API_KEY}
    model: claude-3-sonnet-20240229
    
  backup:
    name: backup
    type: openai
    apiKey: ${OPENAI_API_KEY}
    model: gpt-4

consciousness:
  enabled: true
  provider: default
  awarenessThreshold: 70
  contextWindowSize: 20
  memoryRetentionHours: 24
  personalityTraits:
    curiosity: 80
    helpfulness: 90
    creativity: 70
    analytical: 85
    empathy: 75

security:
  permissionLevel: safe
  allowedCommands:
    - read
    - write
    - analyze
  deniedPaths:
    - /etc
    - /var
    - /sys
    - /proc
  maxExecutionTime: 30000
  maxMemoryUsage: 536870912  # 512MB

storage:
  type: redis
  redis:
    host: localhost
    port: 6379
    password: ${REDIS_PASSWORD}
    db: 0

logging:
  level: info
  format: json
  outputs:
    - type: console
    - type: file
      path: /var/log/asi-code/app.log
      maxSize: 100MB
      maxFiles: 10

monitoring:
  enabled: true
  metrics:
    enabled: true
    port: 9090
  health:
    enabled: true
    interval: 30000
```

### 3. Systemd Service

Create `/etc/systemd/system/asi-code.service`:

```ini
[Unit]
Description=ASI-Code Server
Documentation=https://github.com/asi-team/asi-code
After=network.target
Wants=network.target

[Service]
Type=simple
User=asi-code
Group=asi-code
WorkingDirectory=/home/asi-code/app/asi-code
ExecStart=/home/asi-code/.bun/bin/bun run start
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
KillSignal=SIGINT
TimeoutStopSec=5
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/asi-code/app
NoNewPrivileges=true

# Environment
Environment=NODE_ENV=production
EnvironmentFile=-/home/asi-code/app/asi-code/.env

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Restart policy
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable asi-code
sudo systemctl start asi-code
sudo systemctl status asi-code
```

## Docker Deployment

### 1. Dockerfile

Create a production-ready Dockerfile:

```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder

# Install build dependencies
RUN apk add --no-cache python3 make g++

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json bun.lockb ./

# Install Bun
RUN npm install -g bun

# Install dependencies
RUN bun install --frozen-lockfile

# Copy source code
COPY . .

# Build application
RUN bun run build

# Production stage
FROM node:18-alpine AS production

# Create app user
RUN addgroup -g 1001 -S asi-code && \
    adduser -S asi-code -u 1001

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    tini

# Install Bun
RUN npm install -g bun

# Set working directory
WORKDIR /app

# Copy built application
COPY --from=builder --chown=asi-code:asi-code /app/dist ./dist
COPY --from=builder --chown=asi-code:asi-code /app/bin ./bin
COPY --from=builder --chown=asi-code:asi-code /app/package.json ./
COPY --from=builder --chown=asi-code:asi-code /app/node_modules ./node_modules

# Create logs directory
RUN mkdir -p /var/log/asi-code && \
    chown asi-code:asi-code /var/log/asi-code

# Switch to non-root user
USER asi-code

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Expose port
EXPOSE 3000

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Start application
CMD ["bun", "run", "start"]
```

### 2. Docker Compose

Create `docker-compose.yml` for complete stack:

```yaml
version: '3.8'

services:
  asi-code:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/asicode
    env_file:
      - .env.production
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
    volumes:
      - asi-logs:/var/log/asi-code
    networks:
      - asi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - asi-network
    command: redis-server --appendonly yes

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=asicode
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - asi-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - asi-code
    restart: unless-stopped
    networks:
      - asi-network

volumes:
  redis-data:
  postgres-data:
  asi-logs:

networks:
  asi-network:
    driver: bridge
```

### 3. Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream asi-code {
        server asi-code:3000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ws:10m rate=5r/s;

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # API routes
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://asi-code;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket routes
        location /ws {
            limit_req zone=ws burst=10 nodelay;
            proxy_pass http://asi-code;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check
        location /health {
            proxy_pass http://asi-code;
            access_log off;
        }
    }
}
```

### 4. Deployment Commands

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f asi-code

# Scale service
docker-compose up -d --scale asi-code=3

# Update deployment
docker-compose pull && docker-compose up -d
```

## Kubernetes Deployment

### 1. Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: asi-code
  labels:
    name: asi-code
```

### 2. ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: asi-code-config
  namespace: asi-code
data:
  asi-code.config.yml: |
    server:
      port: 3000
      host: 0.0.0.0
    providers:
      default:
        name: default
        type: anthropic
        apiKey: ${ANTHROPIC_API_KEY}
        model: claude-3-sonnet-20240229
    consciousness:
      enabled: true
      provider: default
    security:
      permissionLevel: safe
    logging:
      level: info
      format: json
```

### 3. Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: asi-code-secrets
  namespace: asi-code
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "your-anthropic-key"
  OPENAI_API_KEY: "your-openai-key"
  JWT_SECRET: "your-jwt-secret"
  REDIS_PASSWORD: "your-redis-password"
```

### 4. Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asi-code
  namespace: asi-code
  labels:
    app: asi-code
spec:
  replicas: 3
  selector:
    matchLabels:
      app: asi-code
  template:
    metadata:
      labels:
        app: asi-code
    spec:
      containers:
      - name: asi-code
        image: asi-code:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: PORT
          value: "3000"
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        envFrom:
        - secretRef:
            name: asi-code-secrets
        volumeMounts:
        - name: config
          mountPath: /app/asi-code.config.yml
          subPath: asi-code.config.yml
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: asi-code-config
---
apiVersion: v1
kind: Service
metadata:
  name: asi-code-service
  namespace: asi-code
spec:
  selector:
    app: asi-code
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP
```

### 5. Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: asi-code-ingress
  namespace: asi-code
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "10"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: asi-code-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: asi-code-service
            port:
              number: 80
```

### 6. Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: asi-code-hpa
  namespace: asi-code
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: asi-code
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 7. Deploy to Kubernetes

```bash
# Apply all configurations
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml

# Check deployment status
kubectl get pods -n asi-code
kubectl get services -n asi-code
kubectl get ingress -n asi-code

# View logs
kubectl logs -f deployment/asi-code -n asi-code
```

## Cloud Deployments

### AWS Deployment

#### Using ECS with Fargate

```yaml
# ecs-task-definition.json
{
  "family": "asi-code",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "asi-code",
      "image": "your-account.dkr.ecr.region.amazonaws.com/asi-code:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "ANTHROPIC_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:asi-code/anthropic-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/aws/ecs/asi-code",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:3000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### CloudFormation Template

```yaml
# cloudformation.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ASI-Code ECS Deployment'

Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  SubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
  DomainName:
    Type: String
    Default: asi-code.example.com

Resources:
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: asi-code-cluster
      CapacityProviders:
        - FARGATE
        - FARGATE_SPOT

  ECSService:
    Type: AWS::ECS::Service
    Properties:
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref TaskDefinition
      LaunchType: FARGATE
      DesiredCount: 2
      NetworkConfiguration:
        AwsvpcConfiguration:
          SecurityGroups:
            - !Ref SecurityGroup
          Subnets: !Ref SubnetIds
      LoadBalancers:
        - ContainerName: asi-code
          ContainerPort: 3000
          TargetGroupArn: !Ref TargetGroup

  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Type: application
      Scheme: internet-facing
      SecurityGroups:
        - !Ref ALBSecurityGroup
      Subnets: !Ref SubnetIds

  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Port: 3000
      Protocol: HTTP
      TargetType: ip
      VpcId: !Ref VpcId
      HealthCheckPath: /health
```

### Azure Deployment

#### Container Instances

```yaml
# azure-container-instances.yaml
apiVersion: 2019-12-01
location: eastus
name: asi-code-container-group
properties:
  containers:
  - name: asi-code
    properties:
      image: your-registry.azurecr.io/asi-code:latest
      ports:
      - port: 3000
        protocol: TCP
      environmentVariables:
      - name: NODE_ENV
        value: production
      - name: PORT
        value: '3000'
      - name: ANTHROPIC_API_KEY
        secureValue: your-api-key
      resources:
        requests:
          cpu: 1
          memoryInGB: 1.5
  osType: Linux
  ipAddress:
    type: Public
    ports:
    - protocol: TCP
      port: 3000
  restartPolicy: Always
tags:
  environment: production
  application: asi-code
type: Microsoft.ContainerInstance/containerGroups
```

#### App Service

```bash
# Deploy to Azure App Service
az webapp create \
  --resource-group asi-code-rg \
  --plan asi-code-plan \
  --name asi-code-app \
  --deployment-container-image-name your-registry.azurecr.io/asi-code:latest

# Configure environment variables
az webapp config appsettings set \
  --resource-group asi-code-rg \
  --name asi-code-app \
  --settings \
    NODE_ENV=production \
    ANTHROPIC_API_KEY=@Microsoft.KeyVault\(SecretUri=https://vault.vault.azure.net/secrets/anthropic-key/\)
```

### Google Cloud Platform

#### Cloud Run Deployment

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: asi-code
  namespace: default
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "1Gi"
        run.googleapis.com/max-scale: "10"
        run.googleapis.com/min-scale: "1"
    spec:
      serviceAccountName: asi-code-sa
      containers:
      - image: gcr.io/your-project/asi-code:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: production
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: asi-code-secrets
              key: anthropic-key
        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
```

Deploy with gcloud:

```bash
# Deploy to Cloud Run
gcloud run deploy asi-code \
  --image gcr.io/your-project/asi-code:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars NODE_ENV=production \
  --set-secrets ANTHROPIC_API_KEY=anthropic-key:latest
```

## Load Balancing

### Nginx Load Balancer

```nginx
# nginx-lb.conf
upstream asi-code-backend {
    least_conn;
    server 10.0.1.10:3000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:3000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:3000 max_fails=3 fail_timeout=30s;
    
    # Health check
    keepalive 32;
}

server {
    listen 80;
    listen 443 ssl http2;
    server_name asi-code.example.com;

    # WebSocket support
    location /ws {
        proxy_pass http://asi-code-backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Sticky sessions for WebSocket
        ip_hash;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://asi-code-backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Connection pooling
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

### HAProxy Configuration

```
# haproxy.cfg
global
    daemon
    maxconn 4096
    log stdout local0

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option httplog

frontend asi-code-frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/asi-code.pem
    redirect scheme https if !{ ssl_fc }
    
    # Route WebSocket connections
    acl is_websocket hdr(Upgrade) -i websocket
    use_backend asi-code-websocket if is_websocket
    
    default_backend asi-code-backend

backend asi-code-backend
    balance roundrobin
    option httpchk GET /health
    
    server asi1 10.0.1.10:3000 check
    server asi2 10.0.1.11:3000 check
    server asi3 10.0.1.12:3000 check

backend asi-code-websocket
    balance source
    option httpchk GET /health
    
    server asi1 10.0.1.10:3000 check
    server asi2 10.0.1.11:3000 check
    server asi3 10.0.1.12:3000 check
```

## Monitoring

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "asi-code-rules.yml"

scrape_configs:
  - job_name: 'asi-code'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "ASI-Code Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(asi_code_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, asi_code_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Active Sessions",
        "type": "stat",
        "targets": [
          {
            "expr": "asi_code_active_sessions",
            "legendFormat": "Sessions"
          }
        ]
      },
      {
        "title": "Consciousness States",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(asi_code_consciousness_level)",
            "legendFormat": "Average Level"
          }
        ]
      }
    ]
  }
}
```

### Health Check Endpoint

ASI-Code provides comprehensive health checks:

```bash
# Basic health check
curl http://localhost:3000/health

# Detailed health check
curl http://localhost:3000/health

# Metrics endpoint
curl http://localhost:3000/metrics
```

## Security

### SSL/TLS Configuration

```bash
# Generate SSL certificate with Let's Encrypt
sudo certbot certonly --standalone \
  -d asi-code.example.com \
  --email admin@example.com \
  --agree-tos \
  --non-interactive

# Set up automatic renewal
sudo crontab -e
# Add: 0 2 * * * certbot renew --quiet
```

### Firewall Configuration

```bash
# UFW firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# iptables rules (alternative)
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP
sudo iptables-save > /etc/iptables/rules.v4
```

### Security Headers

```nginx
# Additional security headers in Nginx
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Referrer-Policy strict-origin-when-cross-origin;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

## Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup-script.sh

BACKUP_DIR="/backup/asi-code"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
pg_dump -U postgres asicode > $BACKUP_DIR/postgres_$DATE.sql

# Backup Redis
redis-cli --rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /home/asi-code/app/asi-code/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Automated Backup with Cron

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /home/asi-code/backup-script.sh

# Weekly full backup on Sunday at 3 AM
0 3 * * 0 /home/asi-code/full-backup-script.sh
```

### Disaster Recovery

```bash
#!/bin/bash
# recovery-script.sh

BACKUP_DIR="/backup/asi-code"
RESTORE_DATE=$1

if [ -z "$RESTORE_DATE" ]; then
    echo "Usage: $0 YYYYMMDD_HHMMSS"
    exit 1
fi

# Stop services
sudo systemctl stop asi-code
sudo systemctl stop postgresql
sudo systemctl stop redis

# Restore PostgreSQL
dropdb -U postgres asicode
createdb -U postgres asicode
psql -U postgres asicode < $BACKUP_DIR/postgres_$RESTORE_DATE.sql

# Restore Redis
redis-cli FLUSHALL
redis-cli --rdb $BACKUP_DIR/redis_$RESTORE_DATE.rdb

# Restore configuration
tar -xzf $BACKUP_DIR/config_$RESTORE_DATE.tar.gz -C /

# Start services
sudo systemctl start postgresql
sudo systemctl start redis
sudo systemctl start asi-code

echo "Recovery completed from backup: $RESTORE_DATE"
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service status
sudo systemctl status asi-code

# Check logs
sudo journalctl -u asi-code -f

# Check configuration
bun run start --check-config

# Test configuration
asi-code --validate-config asi-code.config.yml
```

#### High Memory Usage

```bash
# Monitor memory usage
ps aux | grep asi-code
top -p $(pgrep asi-code)

# Check Node.js heap
curl http://localhost:3000/health | jq '.memory'

# Adjust memory limits
export NODE_OPTIONS="--max-old-space-size=2048"
```

#### Database Connection Issues

```bash
# Test database connectivity
psql -h localhost -U postgres -d asicode -c "SELECT 1;"

# Check Redis connectivity
redis-cli ping

# Verify connection strings
echo $DATABASE_URL
echo $REDIS_URL
```

#### Performance Issues

```bash
# Check system resources
htop
iotop
nethogs

# Monitor application metrics
curl http://localhost:3000/metrics

# Profile application
NODE_ENV=development bun --inspect=0.0.0.0:9229 run start
```

### Log Analysis

```bash
# Real-time log monitoring
tail -f /var/log/asi-code/app.log

# Error analysis
grep -i error /var/log/asi-code/app.log | tail -20

# Performance analysis
grep "response_time" /var/log/asi-code/app.log | \
  awk '{print $5}' | sort -n | tail -10

# Search for specific patterns
jq 'select(.level == "error")' /var/log/asi-code/app.log
```

### Performance Tuning

```bash
# Optimize Node.js settings
export NODE_OPTIONS="--max-old-space-size=2048 --optimize-for-size"

# Adjust system limits
echo "asi-code soft nofile 65536" >> /etc/security/limits.conf
echo "asi-code hard nofile 65536" >> /etc/security/limits.conf

# Tune kernel parameters
echo "net.core.somaxconn = 1024" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 1024" >> /etc/sysctl.conf
sysctl -p
```

---

For additional support and advanced deployment scenarios, please refer to our [documentation](docs/) or contact our support team at support@asi-code.dev.