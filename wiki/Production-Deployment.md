# Production Deployment

**Status**: Design phase (Phase 4.3) | **Issue**: [#164](https://github.com/web3guru888/asi-build/issues/164) | **Discussion**: [#166](https://github.com/web3guru888/asi-build/discussions/166)

Phase 4.3 brings ASI:BUILD from a well-tested research codebase to a production-deployable system. This page documents the deployment architecture, configuration, and operations guide.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/web3guru888/asi-build.git
cd asi-build

# Full stack (all 29 modules, Memgraph, Redis)
docker compose up

# Minimal stack (core cognition: Blackboard + CognitiveCycle + Safety)
docker compose -f docker-compose.yml -f docker-compose.minimal.yml up

# Check health
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/metrics
```

---

## Stack Components

| Service | Image | Port | Role |
|---------|-------|------|------|
| `asi-build` | `./Dockerfile` | 8000 | FastAPI gateway + CognitiveCycle |
| `memgraph` | `memgraph/memgraph` | 7687 | Bi-temporal knowledge graph |
| `redis` | `redis:alpine` | 6379 | MeshTaskQueue persistence + fault history |

### Why Memgraph?

The Cognitive Blackboard is in-memory and intentionally ephemeral (TTL-driven). Memgraph provides persistent storage for the bi-temporal knowledge graph — nodes, edges, and temporal validity ranges that survive restarts.

### Why Redis?

Redis serves two roles distinct from the Blackboard:

1. **MeshTaskQueue persistence** — in-flight tasks survive process restart
2. **CycleFaultSummary rolling window** — last 1,000 tick fault records, used by `/ready`

---

## Docker Compose Configuration

```yaml
# docker-compose.yml
version: "3.9"

services:
  asi-build:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - BLACKBOARD_TTL=300
      - CYCLE_TICK_MS=100
      - CYCLE_TICK_BUDGET_MS=120
      - MESH_MAX_AGENTS=16
      - MESH_QUEUE_CAPACITY=1000
      - REDIS_URL=redis://redis:6379
      - MEMGRAPH_HOST=memgraph
      - MEMGRAPH_PORT=7687
      - MODULES_ENABLED=all          # or: "core,safety,reasoning"
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s
    depends_on:
      memgraph:
        condition: service_healthy
      redis:
        condition: service_healthy

  memgraph:
    image: memgraph/memgraph:latest
    ports:
      - "7687:7687"
    healthcheck:
      test: ["CMD", "echo", "RETURN 1;" | mgconsole]
      interval: 5s
      retries: 5

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5
```

### Minimal Override

```yaml
# docker-compose.minimal.yml
services:
  asi-build:
    environment:
      - MODULES_ENABLED=core,safety,reasoning,blackboard
      - MESH_MAX_AGENTS=4
```

---

## Health & Readiness Endpoints

Three endpoints expose system health at different granularities:

### `GET /health`

**Purpose**: Is the process alive and responding?

Returns 200 as long as FastAPI is serving requests. This is the liveness probe — it does **not** check module health.

```json
{
  "status": "alive",
  "uptime_s": 3612.4,
  "version": "0.1.0-alpha"
}
```

### `GET /ready`

**Purpose**: Is the system ready to serve cognitive requests?

Returns 200 when:
- `CognitiveCycle` has ticked within the last 5 seconds
- `CycleFaultSummary` reports ≥ 20/29 modules healthy
- `AgentDiscovery` shows ≥ 1 agent in HEALTHY state

Returns 503 with a JSON body explaining which condition failed.

```json
{
  "status": "ready",
  "modules_healthy": 27,
  "modules_total": 29,
  "last_tick_s": 0.08,
  "agents_healthy": 4
}
```

### `GET /metrics`

**Purpose**: Prometheus text-format metrics for time-series monitoring.

```
# HELP cycle_tick_duration_ms CognitiveCycle tick wall-clock latency
# TYPE cycle_tick_duration_ms histogram
cycle_tick_duration_ms_bucket{le="1.0"} 0
cycle_tick_duration_ms_bucket{le="5.0"} 12
cycle_tick_duration_ms_bucket{le="10.0"} 847
cycle_tick_duration_ms_bucket{le="50.0"} 9203
cycle_tick_duration_ms_bucket{le="100.0"} 9987
cycle_tick_duration_ms_bucket{le="+Inf"} 10000
```

---

## Prometheus Metrics Reference

### CognitiveCycle

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cycle_tick_duration_ms` | histogram | — | P50/P95/P99 tick latency |
| `cycle_tick_total` | counter | `status` (ok/degraded/fault) | Tick outcomes |
| `cycle_phase_duration_ms` | histogram | `phase` | Per-phase timing |
| `cycle_budget_violations_total` | counter | `phase` | Budget exceeded events |

### AgentMesh

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `mesh_task_dispatched_total` | counter | `priority` | Tasks dispatched |
| `mesh_task_latency_ms` | histogram | — | Dispatch→result wall clock |
| `mesh_queue_depth` | gauge | — | Live backlog depth |
| `mesh_agent_count` | gauge | `state` (HEALTHY/DEGRADED/UNREACHABLE) | Agent counts |
| `mesh_aggregation_dissent_ratio` | histogram | `strategy` | Agent disagreement rate |

### Cognitive Blackboard

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `blackboard_writes_total` | counter | `entry_type` | Entry writes by type |
| `blackboard_read_latency_us` | histogram | — | Microsecond read latency |
| `blackboard_subscribers_active` | gauge | — | Active wildcard subscriptions |

---

## Kubernetes Helm Chart

For production k8s deployments, a Helm chart is provided under `charts/asi-build/`:

```
charts/asi-build/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── configmap.yaml
    ├── hpa.yaml               # scales on cycle_tick_duration_ms P95 > 80ms
    └── servicemonitor.yaml    # Prometheus ServiceMonitor
```

### Install

```bash
# Local kind cluster
kind create cluster
helm install asi-build ./charts/asi-build

# Production with custom values
helm install asi-build ./charts/asi-build \
  --set replicaCount=3 \
  --set resources.limits.memory=4Gi \
  --set autoscaling.enabled=true
```

### HorizontalPodAutoscaler

The HPA scales on custom metric `cycle_tick_duration_ms_p95`:

```yaml
metrics:
  - type: Pods
    pods:
      metric:
        name: cycle_tick_duration_ms_p95
      target:
        type: AverageValue
        averageValue: 80m   # 80ms P95 → scale up
```

---

## CI/CD Smoke Test

A GitHub Actions workflow validates the full deployment on every PR:

```yaml
# .github/workflows/docker-smoke.yml
name: Docker Compose Smoke Test
on: [pull_request]
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start stack
        run: docker compose up -d
      - name: Wait for health
        run: |
          for i in $(seq 1 30); do
            curl -sf http://localhost:8000/health && break
            sleep 2
          done
      - name: Check readiness
        run: curl -f http://localhost:8000/ready
      - name: Tear down
        run: docker compose down
```

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `BLACKBOARD_TTL` | `300` | Default Blackboard entry TTL (seconds) |
| `CYCLE_TICK_MS` | `100` | CognitiveCycle tick interval |
| `CYCLE_TICK_BUDGET_MS` | `120` | Maximum allowed tick wall-clock |
| `MESH_MAX_AGENTS` | `16` | AgentMesh maximum concurrent agents |
| `MESH_QUEUE_CAPACITY` | `1000` | MeshTaskQueue maximum depth |
| `MESH_QUORUM` | `0.5` | Default result quorum for MeshResultAggregator |
| `MODULES_ENABLED` | `all` | Comma-separated module list or `all` |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `MEMGRAPH_HOST` | `localhost` | Memgraph Bolt host |
| `MEMGRAPH_PORT` | `7687` | Memgraph Bolt port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `PROMETHEUS_ENABLED` | `true` | Expose `/metrics` endpoint |

---

## Related Pages

- [Health Monitoring](Health-Monitoring) — CycleFaultSummary, SSE stream
- [Multi-Agent Orchestration](Multi-Agent-Orchestration) — AgentMesh architecture
- [AgentDiscovery](AgentDiscovery) — agent health state machine
- [MeshTaskQueue](MeshTaskQueue) — queue persistence and Redis integration
- [Phase 4 Roadmap](Phase-4-Roadmap) — full Phase 4 milestone tracker
