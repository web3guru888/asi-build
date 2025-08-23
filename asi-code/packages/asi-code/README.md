# 🚀 ASI-Code: Advanced System Intelligence Code Assistant

**Version**: 0.2.0  
**Status**: 85% Production Ready  
**License**: MIT  
**AI Provider**: ASI:One (Fetch.ai)  

> *Intelligent code assistant framework with revolutionary agent orchestration capabilities powered by ASI:One*

## 🌟 Overview

ASI-Code is a cutting-edge AI-powered development framework featuring a complete **Agent Orchestration System** that enables supervisor agents to spawn, manage, and coordinate worker agents for massive parallel task execution. Built with TypeScript and designed for production scalability.

### 🎯 Key Features

- **🤖 Agent Orchestration**: Complete supervisor/worker agent architecture
- **⚡ Parallel Execution**: Task decomposition with intelligent coordination
- **🔧 Tool Integration**: 8+ built-in development tools
- **📊 Real-time Monitoring**: Prometheus metrics, OpenTelemetry tracing
- **🌐 WebSocket Support**: Real-time communication with auto-reconnection
- **💾 Production Database**: PostgreSQL with migrations and transactions
- **🔄 Kenny Integration**: Advanced AI personality and context management
- **🧠 ASI:One Integration**: Powered by Fetch.ai's ASI:One for intelligent AI responses
- **🎨 Web UI Dashboard**: Modern control panel with real-time monitoring

## 🚀 Quick Start

### Prerequisites

- Docker 24.0+
- Kubernetes 1.27+ (or Docker Compose for local deployment)
- kubectl and Helm 3.12+
- Node.js 18+ or Bun 1.0+

### Local Development Setup

```bash
# Clone and setup
git clone <repository-url>
cd asi-code/packages/asi-code

# Setup environment variables
cat > .env << EOF
ASI1_API_KEY=your-asi1-api-key-here
ASI1_MODEL=asi1-mini
PORT=3333
EOF

# Install dependencies
bun install  # or npm install

# Start the ASI-Code server with ASI:One integration
bun asi-code-server-ws-enhanced.ts

# In another terminal, start the Web UI
python3 -m http.server 8888 --directory public

# Access the system
# Web UI: http://localhost:8888
# API: http://localhost:3333
# WebSocket: ws://localhost:3333/ws

# Verify deployment
curl http://localhost:3333/health
```

### Production Deployment

```bash
# Setup production environment
./scripts/setup-environment.sh --environment production

# Apply security hardening
./scripts/security-hardening.sh --environment production

# Deploy to Kubernetes
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -n asi-code
curl https://asi-code.company.com/health
```

## Architecture

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Production Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐│
│  │   Internet  │───▶│ Load Balancer│───▶│   Kubernetes    ││
│  │             │    │   (AWS ELB)  │    │    Cluster     ││
│  └─────────────┘    └──────────────┘    └─────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                 Kubernetes Cluster                      ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐││
│  │  │  ASI-Code   │ │ PostgreSQL  │ │      Redis         │││
│  │  │    Pods     │ │  Database   │ │      Cache         │││
│  │  │             │ │             │ │                    │││
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘││
│  │                                                         ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐││
│  │  │ Prometheus  │ │   Grafana   │ │       Loki         │││
│  │  │ Monitoring  │ │ Dashboards  │ │   Log Aggregation  │││
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Application Stack

- **Runtime**: Node.js/Bun with TypeScript
- **Framework**: Hono.js for HTTP server
- **Database**: PostgreSQL 16+ with connection pooling
- **Cache**: Redis 7+ for sessions and caching
- **Monitoring**: Prometheus + Grafana + Loki
- **Security**: JWT auth, RBAC, network policies

## Deployment Options

### 1. Kubernetes (Production)

**Features**:
- High availability with 3+ replicas
- Auto-scaling (HPA)
- Rolling deployments
- Health checks and self-healing
- Network policies and security contexts

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
kubectl rollout status deployment/asi-code -n asi-code
```

### 2. Docker Compose (Development/Staging)

**Features**:
- Single-command deployment
- Integrated monitoring stack
- Volume persistence
- Easy development workflow

```bash
# Start all services
docker-compose up -d

# Scale application
docker-compose up -d --scale asi-code=3
```

### 3. Helm Charts (Flexible K8s)

**Features**:
- Parameterized deployments
- Environment-specific values
- Dependency management
- Upgrade/rollback support

```bash
# Install with Helm
helm install asi-code ./charts/asi-code \
  --namespace asi-code \
  --create-namespace \
  --values values-production.yaml
```

## Directory Structure

```
asi-code/
├── .github/workflows/     # CI/CD pipelines
│   ├── ci.yml            # Continuous Integration
│   ├── cd.yml            # Continuous Deployment
│   └── security.yml      # Security scanning
├── k8s/                  # Kubernetes manifests
│   ├── namespace.yaml    # Namespace definition
│   ├── deployment.yaml   # Application deployment
│   ├── service.yaml      # Service definitions
│   ├── ingress.yaml      # Ingress configuration
│   ├── configmap.yaml    # Configuration maps
│   ├── secrets.yaml      # Secret templates
│   ├── rbac.yaml         # RBAC configuration
│   ├── pv.yaml           # Persistent volumes
│   ├── postgres.yaml     # Database deployment
│   └── redis.yaml        # Cache deployment
├── monitoring/           # Monitoring configuration
│   ├── prometheus.yml    # Prometheus config
│   ├── alerting-rules.yml# Alert rules
│   ├── loki-config.yml   # Loki configuration
│   ├── promtail-config.yml# Log collection
│   └── grafana/          # Grafana dashboards
├── security/             # Security documentation
│   ├── security-policy.md
│   └── secrets-management.md
├── scripts/              # Operational scripts
│   ├── setup-environment.sh
│   └── security-hardening.sh
├── config/               # Application configuration
│   ├── production.yml    # Production config
│   ├── staging.yml       # Staging config
│   └── default-config.ts # Default configuration
├── docs/                 # Documentation
│   ├── deployment-guide.md
│   └── operational-runbooks.md
├── Dockerfile            # Container definition
├── docker-compose.yml    # Compose configuration
└── .env.example          # Environment template
```

## Configuration

### Environment Variables

Key environment variables for production:

```bash
# Application
NODE_ENV=production
SERVER_PORT=3000
LOG_LEVEL=info

# Security
JWT_SECRET=your-jwt-secret-here
ENCRYPTION_KEY=your-encryption-key-here

# Database
DATABASE_URL=postgresql://user:pass@host:5432/asicode
POSTGRES_PASSWORD=secure-password

# Cache
REDIS_URL=redis://host:6379
REDIS_PASSWORD=secure-password

# AI Services
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key

# Monitoring
SENTRY_DSN=your-sentry-dsn
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
```

### Configuration Files

- **`config/production.yml`**: Production settings
- **`config/staging.yml`**: Staging overrides
- **`.env`**: Environment-specific variables (create from `.env.example`)

## Security

### Security Features

- **Authentication**: JWT-based with configurable expiration
- **Authorization**: Role-based access control (RBAC)
- **Encryption**: AES-256 for data at rest, TLS 1.3 for transit
- **Network Security**: Network policies, ingress controls
- **Container Security**: Non-root user, read-only filesystem
- **Secrets Management**: Kubernetes secrets or external providers
- **Vulnerability Scanning**: Automated dependency and container scanning

### Hardening

Apply security hardening with:

```bash
./scripts/security-hardening.sh --environment production
```

This configures:
- Pod security standards
- Network policies
- RBAC permissions
- Resource quotas
- Security contexts
- SSL certificates

## Monitoring & Observability

### Metrics (Prometheus)

- Application performance metrics
- System resource usage
- Custom business metrics
- Alert rules and thresholds

### Logs (Loki)

- Centralized log aggregation
- Structured logging with JSON
- Log parsing and labeling
- Retention and archival

### Dashboards (Grafana)

- Application performance dashboard
- Infrastructure monitoring
- Business metrics
- Alert visualization

### Tracing (Jaeger)

- Distributed request tracing
- Performance bottleneck identification
- Service dependency mapping
- Error tracking

Access monitoring:

```bash
# Port forward to access locally
kubectl port-forward svc/grafana 3000:3000 -n monitoring
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
kubectl port-forward svc/jaeger 16686:16686 -n monitoring
```

## CI/CD Pipeline

### GitHub Actions Workflows

1. **CI Pipeline** (`.github/workflows/ci.yml`):
   - Code quality checks (ESLint, Prettier)
   - Security scanning (CodeQL, Trivy)
   - Unit and integration tests
   - Docker image building
   - Vulnerability assessments

2. **CD Pipeline** (`.github/workflows/cd.yml`):
   - Automated deployments to staging/production
   - Blue-green deployment strategy
   - Database migrations
   - Health checks and rollback

3. **Security Pipeline** (`.github/workflows/security.yml`):
   - SAST/DAST scanning
   - Dependency vulnerability checks
   - Container security scanning
   - Compliance reporting

### Deployment Strategies

- **Rolling Deployment**: Zero-downtime updates (default)
- **Blue-Green**: Full environment switching (production)
- **Canary**: Gradual rollout with traffic splitting

## Operations

### Health Monitoring

```bash
# Application health
curl https://asi-code.company.com/health

# Kubernetes health
kubectl get pods -n asi-code
kubectl top pods -n asi-code
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment asi-code --replicas=5 -n asi-code

# Auto-scaling (HPA configured)
kubectl get hpa -n asi-code
```

### Backup & Recovery

```bash
# Database backup
kubectl exec deployment/postgres -n asi-code -- \
  pg_dump -U asicode asicode > backup.sql

# Restore from backup
kubectl exec -i deployment/postgres -n asi-code -- \
  psql -U asicode asicode < backup.sql
```

### Log Access

```bash
# Application logs
kubectl logs -f deployment/asi-code -n asi-code

# All component logs
kubectl logs -f -l app=asi-code -n asi-code --all-containers
```

## Troubleshooting

### Common Issues

1. **Application won't start**
   ```bash
   kubectl describe pod <pod-name> -n asi-code
   kubectl logs <pod-name> -n asi-code
   ```

2. **Database connection issues**
   ```bash
   kubectl exec deployment/asi-code -n asi-code -- \
     pg_isready -h postgres -U asicode
   ```

3. **High memory usage**
   ```bash
   kubectl top pods -n asi-code
   kubectl describe pod <pod-name> -n asi-code
   ```

### Support

- **Documentation**: See `docs/` directory
- **Runbooks**: `docs/operational-runbooks.md`
- **Security**: `security/security-policy.md`
- **Issues**: GitHub Issues
- **Emergency**: Contact on-call engineer

## Development

### Local Development

```bash
# Setup development environment
./scripts/setup-environment.sh --environment development

# Start dependencies
docker-compose up -d postgres redis

# Run application
bun run dev
```

### Testing

```bash
# Unit tests
bun test

# Integration tests
bun test:integration

# Security tests
bun run security-scan
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run CI checks locally
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For production support and questions:

- **Documentation**: [docs/deployment-guide.md](docs/deployment-guide.md)
- **Operations**: [docs/operational-runbooks.md](docs/operational-runbooks.md)
- **Security**: [security/security-policy.md](security/security-policy.md)
- **Issues**: Create a GitHub issue
- **Emergency**: Contact your operations team

---

**ASI-Code** - Advanced AI-powered development framework, production-ready and enterprise-grade.