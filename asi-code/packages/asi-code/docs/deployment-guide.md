# ASI-Code Production Deployment Guide

## Overview

This comprehensive guide provides step-by-step instructions for deploying ASI-Code to production environments using Kubernetes, Docker, and supporting infrastructure.

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 4 cores
- **Memory**: 8GB RAM
- **Storage**: 100GB SSD
- **Network**: 1 Gbps

#### Recommended Requirements (Production)
- **CPU**: 8+ cores
- **Memory**: 16GB+ RAM
- **Storage**: 500GB+ NVMe SSD
- **Network**: 10 Gbps
- **High Availability**: Multi-zone deployment

### Software Requirements

#### Required Tools
- Docker 24.0+
- Docker Compose 2.20+
- Kubernetes 1.27+
- kubectl 1.27+
- Helm 3.12+
- OpenSSL 1.1.1+

#### Optional Tools
- Terraform (for infrastructure)
- Ansible (for configuration management)
- Vault (for secrets management)

### Cloud Provider Support
- AWS EKS
- Google GKE
- Azure AKS
- DigitalOcean Kubernetes
- On-premises Kubernetes

## Deployment Methods

### Method 1: Kubernetes Deployment (Recommended for Production)

#### 1. Prepare Environment
```bash
# Clone the repository
git clone https://github.com/your-org/asi-code.git
cd asi-code/packages/asi-code

# Set up environment
./scripts/setup-environment.sh --environment production

# Apply security hardening
./scripts/security-hardening.sh --environment production
```

#### 2. Configure Secrets
```bash
# Create Kubernetes secrets
kubectl create namespace asi-code

# Create database secret
kubectl create secret generic asi-code-secrets \
  --from-literal=DATABASE_URL="postgresql://user:pass@host:5432/db" \
  --from-literal=REDIS_URL="redis://host:6379" \
  --from-literal=JWT_SECRET="your-jwt-secret" \
  --from-literal=ANTHROPIC_API_KEY="your-api-key" \
  --namespace=asi-code

# Or use external secret manager (recommended)
kubectl apply -f k8s/secrets.yaml
```

#### 3. Deploy Infrastructure Components
```bash
# Apply namespace and RBAC
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml

# Deploy storage
kubectl apply -f k8s/pv.yaml

# Deploy database
kubectl apply -f k8s/postgres.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l component=database -n asi-code --timeout=300s

# Deploy cache
kubectl apply -f k8s/redis.yaml

# Wait for cache to be ready
kubectl wait --for=condition=ready pod -l component=cache -n asi-code --timeout=180s
```

#### 4. Deploy Application
```bash
# Apply configuration
kubectl apply -f k8s/configmap.yaml

# Deploy main application
kubectl apply -f k8s/deployment.yaml

# Deploy services
kubectl apply -f k8s/service.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Wait for deployment
kubectl rollout status deployment/asi-code -n asi-code --timeout=600s
```

#### 5. Verify Deployment
```bash
# Check all pods are running
kubectl get pods -n asi-code

# Check services
kubectl get services -n asi-code

# Test health endpoint
kubectl port-forward service/asi-code 8080:80 -n asi-code &
curl -f http://localhost:8080/health

# Check logs
kubectl logs -f deployment/asi-code -n asi-code
```

### Method 2: Docker Compose Deployment (Staging/Development)

#### 1. Prepare Environment
```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Generate secure secrets
./scripts/setup-environment.sh --environment staging
```

#### 2. Deploy with Docker Compose
```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f asi-code

# Test deployment
curl -f http://localhost:3000/health
```

#### 3. Initialize Database
```bash
# Run database migrations
docker-compose exec asi-code bun run migrate

# Verify database connection
docker-compose exec postgres psql -U asicode -d asicode -c "SELECT version();"
```

### Method 3: Helm Deployment

#### 1. Add Helm Repository
```bash
# Add ASI-Code Helm repository (if available)
helm repo add asi-code https://charts.asi-code.company.com
helm repo update
```

#### 2. Prepare Values File
```yaml
# values-production.yaml
global:
  environment: production
  imageTag: "v1.0.0"

asicode:
  replicaCount: 3
  image:
    repository: ghcr.io/your-org/asi-code
    tag: "v1.0.0"
  
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

  env:
    NODE_ENV: production
    LOG_LEVEL: info

postgresql:
  enabled: true
  auth:
    database: asicode
    username: asicode
  primary:
    persistence:
      size: 100Gi

redis:
  enabled: true
  auth:
    enabled: true
  master:
    persistence:
      size: 20Gi

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: asi-code.company.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: asi-code-tls
      hosts:
        - asi-code.company.com
```

#### 3. Deploy with Helm
```bash
# Install ASI-Code
helm install asi-code asi-code/asi-code \
  --namespace asi-code \
  --create-namespace \
  --values values-production.yaml

# Check deployment status
helm status asi-code -n asi-code

# Upgrade deployment
helm upgrade asi-code asi-code/asi-code \
  --namespace asi-code \
  --values values-production.yaml
```

## Environment-Specific Configurations

### Production Environment

#### High Availability Setup
```yaml
# Multi-zone deployment
nodeSelector:
  topology.kubernetes.io/zone: us-west-2a

affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app
          operator: In
          values: ["asi-code"]
      topologyKey: kubernetes.io/hostname
```

#### Auto-scaling Configuration
```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: asi-code-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: asi-code
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### Monitoring and Alerting
```bash
# Deploy monitoring stack
kubectl apply -f monitoring/prometheus.yml
kubectl apply -f monitoring/grafana/
kubectl apply -f monitoring/alerting-rules.yml

# Access Grafana dashboard
kubectl port-forward service/grafana 3000:3000
# Open http://localhost:3000 (admin/admin)
```

### Staging Environment

#### Resource Optimization
```yaml
# Reduced resources for staging
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 2Gi

# Single replica for cost savings
replicas: 1
```

#### Development Features
```yaml
# Enable debug mode
env:
  - name: LOG_LEVEL
    value: debug
  - name: DEBUG_MODE
    value: "true"
```

## Database Setup

### PostgreSQL Configuration

#### Production Database Setup
```sql
-- Create database and user
CREATE DATABASE asicode;
CREATE USER asicode WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE asicode TO asicode;

-- Enable required extensions
\c asicode;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
```

#### Database Migrations
```bash
# Run migrations
docker-compose exec asi-code bun run migrate

# Or in Kubernetes
kubectl exec deployment/asi-code -n asi-code -- bun run migrate
```

#### Backup Configuration
```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DB_NAME="asicode"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

pg_dump -h postgres -U asicode -d "$DB_NAME" > "$BACKUP_DIR/backup_$DATE.sql"
gzip "$BACKUP_DIR/backup_$DATE.sql"

# Keep only last 7 days
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +7 -delete
```

### Redis Configuration

#### Production Redis Setup
```bash
# Redis configuration for production
cat <<EOF > redis.conf
bind 0.0.0.0
port 6379
requirepass your_secure_password
appendonly yes
appendfsync everysec
maxmemory 2gb
maxmemory-policy allkeys-lru
EOF
```

## Security Configuration

### TLS/SSL Setup

#### Certificate Management
```bash
# Using cert-manager with Let's Encrypt
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@company.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

#### Manual Certificate Setup
```bash
# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -keyout tls.key -out tls.crt -days 365 -nodes

# Create Kubernetes secret
kubectl create secret tls asi-code-tls --cert=tls.crt --key=tls.key -n asi-code
```

### Network Security

#### Network Policies
```yaml
# Default deny all traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: asi-code
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

#### Firewall Rules (Cloud Provider)
```bash
# AWS Security Group rules
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Allow internal cluster communication
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 \
  --protocol tcp \
  --port 3000 \
  --source-group sg-87654321
```

## Monitoring and Observability

### Prometheus Setup
```bash
# Deploy Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### Grafana Dashboard
```bash
# Access Grafana
kubectl port-forward service/prometheus-grafana 3000:80 -n monitoring

# Import ASI-Code dashboard
# Use the dashboard JSON from monitoring/grafana/provisioning/dashboards/
```

### Log Aggregation
```bash
# Deploy Loki
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --namespace logging \
  --create-namespace
```

## Load Testing and Performance

### Performance Testing
```bash
# Install k6 for load testing
docker pull grafana/k6

# Create load test script
cat <<EOF > load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 50,
  duration: '30s',
};

export default function () {
  const response = http.get('https://asi-code.company.com/health');
  check(response, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}
EOF

# Run load test
docker run --rm -v $(pwd):/scripts grafana/k6 run /scripts/load-test.js
```

### Performance Tuning
```yaml
# Application performance tuning
env:
- name: NODE_MAX_OLD_SPACE_SIZE
  value: "4096"
- name: UV_THREADPOOL_SIZE
  value: "16"

# JVM tuning for containers
- name: JAVA_OPTS
  value: "-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"
```

## Backup and Disaster Recovery

### Automated Backup Strategy

#### Database Backups
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: asi-code
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:16-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres -U asicode asicode > /backup/backup-$(date +%Y%m%d_%H%M%S).sql
              find /backup -name "backup-*.sql" -mtime +7 -delete
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

#### Application Data Backups
```bash
# Backup script for application data
#!/bin/bash
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/asi-code/$BACKUP_DATE"

mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump -h localhost -U asicode asicode > "$BACKUP_DIR/database.sql"

# Backup Redis data
redis-cli --rdb "$BACKUP_DIR/redis.rdb"

# Backup uploaded files
tar -czf "$BACKUP_DIR/files.tar.gz" /app/data/uploads/

# Upload to cloud storage
aws s3 cp "$BACKUP_DIR" s3://asi-code-backups/$(date +%Y/%m/%d)/ --recursive

# Cleanup local backups older than 3 days
find /backups/asi-code -type d -mtime +3 -exec rm -rf {} \;
```

### Disaster Recovery Procedures

#### Recovery Testing
```bash
# Test database restore
pg_restore -h localhost -U asicode -d asicode_test backup.sql

# Test application startup with restored data
docker-compose -f docker-compose.test.yml up -d
```

#### Failover Procedures
1. **Database Failover**
   - Promote read replica to master
   - Update application configuration
   - Restart application pods

2. **Application Failover**
   - Switch traffic to backup region
   - Scale up backup environment
   - Monitor performance metrics

## Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check pod status
kubectl get pods -n asi-code

# Check pod logs
kubectl logs -f deployment/asi-code -n asi-code

# Check events
kubectl get events -n asi-code --sort-by='.lastTimestamp'

# Common fixes:
# 1. Check environment variables
kubectl exec deployment/asi-code -n asi-code -- env | grep ASI

# 2. Check database connectivity
kubectl exec deployment/asi-code -n asi-code -- pg_isready -h postgres

# 3. Check Redis connectivity
kubectl exec deployment/asi-code -n asi-code -- redis-cli -h redis ping
```

#### Performance Issues
```bash
# Check resource usage
kubectl top pods -n asi-code
kubectl top nodes

# Check application metrics
kubectl port-forward service/asi-code 9090:9090 -n asi-code
# Visit http://localhost:9090/metrics

# Check database performance
kubectl exec deployment/postgres -n asi-code -- \
  psql -U asicode -c "SELECT * FROM pg_stat_activity;"
```

#### Memory Issues
```bash
# Check memory usage
kubectl exec deployment/asi-code -n asi-code -- cat /proc/meminfo

# Check Node.js heap
kubectl exec deployment/asi-code -n asi-code -- \
  node -e "console.log(process.memoryUsage())"

# Increase memory limits if needed
kubectl patch deployment asi-code -n asi-code --patch='
spec:
  template:
    spec:
      containers:
      - name: asi-code
        resources:
          limits:
            memory: "4Gi"
'
```

### Debugging Guide

#### Application Debugging
```bash
# Enable debug mode
kubectl patch deployment asi-code -n asi-code --patch='
spec:
  template:
    spec:
      containers:
      - name: asi-code
        env:
        - name: LOG_LEVEL
          value: debug
        - name: DEBUG_MODE
          value: "true"
'

# Access application shell
kubectl exec -it deployment/asi-code -n asi-code -- /bin/bash

# Check configuration
kubectl exec deployment/asi-code -n asi-code -- cat /app/config/production.yml
```

#### Database Debugging
```bash
# Check database connections
kubectl exec deployment/postgres -n asi-code -- \
  psql -U asicode -c "SELECT pid, usename, application_name, client_addr, state FROM pg_stat_activity;"

# Check database locks
kubectl exec deployment/postgres -n asi-code -- \
  psql -U asicode -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Check database performance
kubectl exec deployment/postgres -n asi-code -- \
  psql -U asicode -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Weekly Tasks
- Review application logs
- Check security alerts
- Update monitoring dashboards
- Review resource usage

#### Monthly Tasks
- Rotate secrets and certificates
- Update dependencies
- Run security scans
- Review backup integrity

#### Quarterly Tasks
- Conduct disaster recovery tests
- Review and update documentation
- Perform security audits
- Update monitoring and alerting rules

### Update Procedures

#### Application Updates
```bash
# 1. Test in staging first
kubectl set image deployment/asi-code asi-code=asi-code:v1.1.0 -n asi-code-staging

# 2. Deploy to production with rolling update
kubectl set image deployment/asi-code asi-code=asi-code:v1.1.0 -n asi-code

# 3. Monitor deployment
kubectl rollout status deployment/asi-code -n asi-code

# 4. Rollback if needed
kubectl rollout undo deployment/asi-code -n asi-code
```

#### Database Schema Updates
```bash
# 1. Backup database
kubectl exec deployment/postgres -n asi-code -- \
  pg_dump -U asicode asicode > backup-pre-migration.sql

# 2. Run migrations
kubectl exec deployment/asi-code -n asi-code -- bun run migrate

# 3. Verify migration success
kubectl exec deployment/asi-code -n asi-code -- bun run migrate:status
```

## Support and Escalation

### Support Contacts
- **Level 1 Support**: support@company.com
- **Level 2 Support**: devops@company.com
- **Level 3 Support**: engineering@company.com
- **Emergency**: +1-555-EMERGENCY

### Escalation Procedures
1. **Level 1**: Check logs and common issues (0-30 minutes)
2. **Level 2**: System debugging and configuration (30 minutes - 2 hours)
3. **Level 3**: Code-level debugging and hotfixes (2+ hours)
4. **Critical**: Immediate escalation for security or data loss issues

### Documentation and Resources
- **Internal Wiki**: https://wiki.company.com/asi-code
- **Runbooks**: https://runbooks.company.com/asi-code
- **Monitoring**: https://grafana.company.com
- **Status Page**: https://status.company.com

This deployment guide provides comprehensive instructions for deploying ASI-Code in production environments. Regular updates to this documentation ensure it remains current with system changes and best practices.