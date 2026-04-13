# Phase 8.4 — Docker/Helm: Containerisation & Kubernetes Deployment

Phase 8.4 delivers production-grade containerisation (multi-stage `Dockerfile`), local-dev orchestration (`docker-compose.yml`), and a Kubernetes Helm chart for the full ASI-Build stack.  It is the fourth sub-phase of Phase 8 (Deployment & Introspection).

---

## Motivation

| Gap | Solution |
|-----|---------|
| No reproducible runtime environment | Multi-stage `Dockerfile`, pinned base image |
| Local dev friction (seven services) | `docker-compose.yml` one-command stack |
| No auto-scaling / self-healing | Helm chart with HPA + liveness/readiness probes |
| No in-cluster metrics scraping | Prometheus `ServiceMonitor` CRD |
| No resource quotas | `resources:` limits in every Deployment |

---

## Dockerfile — multi-stage

```dockerfile
# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.11-slim
ARG ASI_VERSION=dev

# ── Stage 0: builder ──────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION} AS builder
WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .
RUN python -m compileall -q asi/

# ── Stage 1: runtime ──────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION} AS runtime
ARG ASI_VERSION
LABEL org.opencontainers.image.version=${ASI_VERSION} \
      org.opencontainers.image.source="https://github.com/web3guru888/asi-build"

RUN useradd -u 1000 -m asi
WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /build/asi ./asi
COPY --from=builder /build/config ./config

USER asi

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "-m", "uvicorn", "asi.explain_api.app:app",
     "--host", "0.0.0.0", "--port", "8080"]
```

Key design decisions:
- `--prefix=/install` keeps site-packages separate → clean `COPY` in stage 1
- `USER asi` (uid 1000) — never run as root in production
- `HEALTHCHECK` uses only stdlib (no `curl`/`wget` in slim image)
- Final image target: **≤ 350 MB**

---

## docker-compose.yml — local dev stack

```yaml
version: "3.9"

services:
  asi-core:
    build: { context: ., args: { ASI_VERSION: "${ASI_VERSION:-dev}" } }
    command: ["python", "-m", "asi.cognitive_cycle"]
    volumes:
      - traces:/app/data/traces
    depends_on:
      redis: { condition: service_healthy }

  explain-api:
    build: { context: ., args: { ASI_VERSION: "${ASI_VERSION:-dev}" } }
    ports: ["8080:8080"]
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s
    depends_on:
      asi-core: { condition: service_started }
      redis:    { condition: service_healthy }

  prometheus:
    image: prom/prometheus:v2.51.0
    volumes: ["./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro"]
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:10.4.0
    volumes: ["./config/grafana:/etc/grafana/provisioning:ro"]
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

volumes:
  traces:
```

---

## Helm chart structure

```
charts/asi-build/
├── Chart.yaml              # apiVersion: v2, appVersion from ASI_VERSION
├── values.yaml             # all tunable knobs
└── templates/
    ├── _helpers.tpl
    ├── deployment.yaml     # asi-core + explain-api sidecars
    ├── service.yaml        # ClusterIP exposing port 8080 + 9100
    ├── ingress.yaml        # optional nginx ingress (disabled by default)
    ├── hpa.yaml            # HorizontalPodAutoscaler (autoscaling/v2)
    ├── configmap.yaml      # prometheus.yml + Grafana dashboard JSON
    └── servicemonitor.yaml # Prometheus Operator ServiceMonitor CRD
```

### values.yaml — key knobs

```yaml
image:
  repository: ghcr.io/web3guru888/asi-build
  tag: latest
  pullPolicy: IfNotPresent

replicaCount: 2

resources:
  requests: { cpu: 500m, memory: 512Mi }
  limits:   { cpu: 2,    memory: 2Gi  }

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 8
  targetCPUUtilizationPercentage: 70

explainApi:
  port: 8080
  rateLimitPerMinute: 60

prometheus:
  serviceMonitor:
    enabled: true
    interval: 15s
```

---

## HorizontalPodAutoscaler (autoscaling/v2)

```yaml
# templates/hpa.yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "asi-build.fullname" . }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "asi-build.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
```

Use `autoscaling/v2` (stable since Kubernetes 1.26) — not the deprecated `v2beta2`.

**Scaling math** (with `targetCPUUtilizationPercentage: 70`, `requests.cpu: 500m`):

```
desiredReplicas = ceil(currentReplicas × currentCPU% / target%)
                = ceil(2 × 85% / 70%)  →  3
```

Peak: `8 × 500m = 4 vCPU` — fits a 3-node cluster with 2 CPUs each.

---

## Prometheus ServiceMonitor

```yaml
# templates/servicemonitor.yaml
{{- if .Values.prometheus.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "asi-build.fullname" . }}
  labels:
    release: kube-prometheus-stack   # must match operator's serviceMonitorSelector
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "asi-build.name" . }}
  endpoints:
    - port: metrics
      interval: {{ .Values.prometheus.serviceMonitor.interval }}
      path: /metrics
{{- end }}
```

> ⚠️ The `release: kube-prometheus-stack` label is **required** — the Prometheus Operator ignores ServiceMonitors without it matching `serviceMonitorSelector`.

---

## prometheus.yml scrape config

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: explain_api
    static_configs:
      - targets: ["explain-api:8080"]
  - job_name: asi_core
    static_configs:
      - targets: ["asi-core:9100"]
    # Covers: causal_graph, decision_tracer, sleep_orchestrator,
    #         replay_buffer, hyper_controller metrics
```

---

## Liveness / readiness probes

```yaml
# templates/deployment.yaml (excerpt)
containers:
  - name: explain-api
    livenessProbe:
      httpGet: { path: /health, port: 8080 }
      initialDelaySeconds: 15
      periodSeconds: 20
      failureThreshold: 3
    readinessProbe:
      httpGet: { path: /health, port: 8080 }
      initialDelaySeconds: 5
      periodSeconds: 10
      successThreshold: 1
```

Liveness failure → pod restart. Readiness failure → removed from Service endpoints (no traffic) but not restarted.

---

## Makefile targets

| Target | Command |
|--------|---------|
| `make docker-build` | `docker build --build-arg ASI_VERSION=$(VERSION) -t asi-build:$(VERSION) .` |
| `make docker-push` | push to GHCR |
| `make compose-up` | `docker compose up -d` |
| `make compose-down` | `docker compose down -v` |
| `make helm-lint` | `helm lint charts/asi-build` |
| `make helm-install` | `helm upgrade --install asi-build charts/asi-build -f values.yaml` |
| `make helm-template` | render manifests to stdout |

---

## GitHub Actions workflow (.github/workflows/docker.yml)

```yaml
name: Docker + Helm CI
on:
  push: { branches: [main] }
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: ${{ github.event_name != 'pull_request' }}
          platforms: linux/amd64,linux/arm64
          tags: ghcr.io/web3guru888/asi-build:${{ github.sha }}
          build-args: ASI_VERSION=${{ github.sha }}

  helm-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-helm@v4
      - run: helm lint charts/asi-build
      - run: helm template asi-build charts/asi-build | kubectl apply --dry-run=client -f -

  cve-scan:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: docker/scout-action@v1
        with:
          command: cves
          image: ghcr.io/web3guru888/asi-build:${{ github.sha }}
          exit-code: true
          only-severities: critical
```

---

## Prometheus metrics (Phase 8.4)

| Metric | Type | Description |
|--------|------|-------------|
| `asi_docker_build_duration_seconds` | Histogram | CI `docker build` wall time |
| `asi_image_size_bytes` | Gauge | Final image size after build |
| `asi_helm_install_duration_seconds` | Histogram | `helm upgrade --install` wall time |
| `asi_pod_restarts_total` | Counter | Pod restart events (liveness failures) |
| `asi_hpa_replica_count` | Gauge | Current HPA replica count |

### PromQL — key queries

```promql
# Pod restart alert (> 3 in 10 min → page)
increase(asi_pod_restarts_total[10m]) > 3

# Current replica count
asi_hpa_replica_count

# Docker build duration P95
histogram_quantile(0.95, rate(asi_docker_build_duration_seconds_bucket[1h]))

# Image size trend
asi_image_size_bytes
```

---

## Acceptance criteria / test targets

1. `docker build .` exits 0, no warnings
2. `docker image inspect` → size ≤ 350 MB
3. `docker run --rm asi-build pytest -x` → all tests pass
4. `docker compose config` → valid YAML
5. `docker compose up -d && curl -f http://localhost:8080/health` → HTTP 200
6. `docker compose ps` → all 5 services healthy
7. `helm lint charts/asi-build` exits 0
8. `helm template` → valid YAML (kubectl dry-run)
9. `helm install --dry-run` → no errors
10. HPA `minReplicas`/`maxReplicas` respected (kind cluster)
11. ServiceMonitor discovered by Prometheus Operator (kube-prometheus-stack)
12. `docker scout cves` → 0 CRITICAL CVEs

---

## 10-step implementation order

1. Write `requirements.txt` (pinned via `pip-compile`)
2. Write `Dockerfile` + `.dockerignore`
3. Write `docker-compose.yml` + `config/prometheus.yml`
4. `docker build` + `docker compose up` locally — fix issues
5. Scaffold `charts/asi-build/` with `helm create`, replace templates
6. Write `templates/deployment.yaml` with probes + resource limits
7. Write `templates/hpa.yaml` + `templates/servicemonitor.yaml`
8. Write `templates/configmap.yaml` (prometheus.yml + Grafana JSON)
9. Write `Makefile` + `.github/workflows/docker.yml`
10. `helm lint` + `docker scout` + `actionlint` — iterate until clean

---

## Phase 8 roadmap

| Sub-phase | Issue | Status |
|-----------|-------|--------|
| 8.1 DecisionTracer | #276 | ✅ spec complete |
| 8.2 CausalGraph | #280 | ✅ spec complete |
| 8.3 ExplainAPI | #283 | ✅ spec complete |
| **8.4 Docker/Helm** | #291 | 🟡 in progress |
| 8.5 Sepolia CI | TBD | 📋 planned |

---

## Related discussions

- #292 Show & Tell: Docker/Helm architecture deep-dive
- #293 Q&A: Docker/Helm configuration questions
- #294 Ideas: Phase 8.5 Sepolia CI pipeline design
- #290 Ideas: Phase 8.4 vs 8.5 planning (original)
