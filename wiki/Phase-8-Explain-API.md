# Phase 8.3 — ExplainAPI: HTTP Introspection Layer

> **Phase**: 8.3 of 8.5  
> **Issue**: [#283](https://github.com/web3guru888/asi-build/issues/283)  
> **Dependencies**: Phase 8.1 ([Decision Tracer](Phase-8-Decision-Tracer)), Phase 8.2 ([Causal Graph](Phase-8-Causal-Graph))  
> **Discussions**: [Show & Tell #284](https://github.com/web3guru888/asi-build/discussions/284) · [Q&A #285](https://github.com/web3guru888/asi-build/discussions/285) · [Ideas #286](https://github.com/web3guru888/asi-build/discussions/286)

---

## Overview

`ExplainAPI` is a **FastAPI-based ASGI application** that exposes the Phase 8
introspection subsystem—`DecisionTracer` and `CausalGraph`—via a stable HTTP interface.

External monitoring tools, operator dashboards, and audit scripts can query:

- **Why** the agent made a particular decision (`GET /traces/{id}/explain`)
- **The causal DAG** at a point in time (`GET /graph/snapshot`)
- **Ancestor/descendant chains** for any cognitive module (`GET /graph/ancestors/{node_id}`)
- **Paginated trace logs** for replay or compliance audit (`GET /traces`)

The app is a **pure factory** — no singletons, no global state — which keeps tests
fully isolated.

---

## Module layout

```
asi/
  phase8/
    explain_metrics.py    # Prometheus metric pre-init
    explain_models.py     # Pydantic v2 response models
    explain_auth.py       # APIKeyAuth + TokenBucket rate limiter
    explain_api.py        # build_explain_app() factory + all routes
tests/
  phase8/
    test_explain_api.py   # 12 tests (httpx.AsyncClient + ASGITransport)
```

---

## Components

### `build_explain_app()` — factory function

```python
def build_explain_app(
    tracer: DecisionTracer,
    graph: CausalGraph,
    api_keys: frozenset[str],
    rate_limit_rps: float = 20.0,
    registry: CollectorRegistry | None = None,
) -> FastAPI:
```

Wires `DecisionTracer` and `CausalGraph` into a single ASGI app with all 9 routes,
authentication, rate limiting, and Prometheus instrumentation.

---

### `APIKeyAuth` — dependency-injectable authenticator

```python
class APIKeyAuth:
    def __init__(self, valid_keys: frozenset[str], rate_limit_rps: float) -> None: ...

    async def __call__(
        self,
        x_api_key: str = Header(..., alias="X-Api-Key"),
    ) -> str:
        if x_api_key not in self._keys:
            raise HTTPException(status_code=401, detail="Invalid API key")
        async with self._lock:
            allowed = self._buckets[x_api_key].consume()
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return x_api_key
```

Used as `Depends(auth)` on every authenticated route. One instance per app.

---

### `TokenBucket` — per-key rate limiter

```python
@dataclass
class TokenBucket:
    rate: float       # tokens per second (= max_rps)
    capacity: float   # burst capacity (= rate × 1 second)

    def consume(self) -> bool:
        now = time.monotonic()
        self._tokens = min(self.capacity, self._tokens + (now - self._last_refill) * self.rate)
        self._last_refill = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False
```

Separate bucket per API key — one misbehaving key cannot exhaust quota for others.  
Under `asyncio.Lock` for safe concurrent access within the event loop.

---

## REST endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | ❌ | Liveness probe → `{"status": "ok"}` |
| `GET` | `/metrics` | ❌ | Prometheus text format |
| `GET` | `/traces` | ✅ | Paginated trace list |
| `GET` | `/traces/{id}` | ✅ | Single trace by ID |
| `GET` | `/traces/{id}/explain` | ✅ | Human-readable explanation |
| `GET` | `/graph/snapshot` | ✅ | Full `CausalGraphSnapshot` |
| `GET` | `/graph/ancestors/{node_id}` | ✅ | BFS ancestor chain |
| `GET` | `/graph/descendants/{node_id}` | ✅ | BFS descendant chain |
| `GET` | `/graph/critical-path` | ✅ | Longest critical path |

### Query parameters

| Route | Param | Type | Default | Max |
|-------|-------|------|---------|-----|
| `/traces` | `since` | `int` (Unix ms) | `None` | — |
| `/traces` | `limit` | `int` | `50` | `200` |
| `/graph/ancestors/{id}` | `max_depth` | `int` | `10` | `50` |
| `/graph/descendants/{id}` | `max_depth` | `int` | `10` | `50` |

---

## Response models (Pydantic v2)

```python
class ContributorResponse(BaseModel):
    module_id: str
    weight: float
    metadata: dict[str, str] = Field(default_factory=dict)

class TraceResponse(BaseModel):
    trace_id: str
    phase: str
    timestamp_ms: int
    contributors: list[ContributorResponse]
    explanation: str | None = None

class TracesListResponse(BaseModel):
    items: list[TraceResponse]
    total: int

class GraphSnapshotResponse(BaseModel):
    node_count: int
    edge_count: int
    root_ids: list[str]
    leaf_ids: list[str]
    max_depth: int

class AncestorResponse(BaseModel):
    node_id: str
    ancestors: list[str]   # also used for descendants
    depth: int

class CriticalPathResponse(BaseModel):
    path: list[str]
    total_weight: float
```

---

## Authentication flow

```
Client ──► GET /traces
           X-Api-Key: my-secret-key
                │
                ▼
         APIKeyAuth.__call__()
                │
          key in valid_keys? ──No──► 401 Unauthorized
                │
               Yes
                │
          TokenBucket.consume() ──False──► 429 Too Many Requests
                │
              True  ──► route handler executes
```

---

## Graph traversal (`ancestors` / `descendants`)

BFS with depth cap, added as convenience methods on `CausalGraph`:

```python
def ancestors(self, node_id: str, max_depth: int = 10) -> list[str]:
    """BFS traversal up the DAG (towards roots)."""
    visited, queue, depth_map = set(), deque([node_id]), {node_id: 0}
    result: list[str] = []
    while queue:
        current = queue.popleft()
        for pred in self._in_edges.get(current, []):
            if pred not in visited:
                d = depth_map[current] + 1
                if d <= max_depth:
                    visited.add(pred)
                    depth_map[pred] = d
                    queue.append(pred)
                    result.append(pred)
    return result

def descendants(self, node_id: str, max_depth: int = 10) -> list[str]:
    """BFS traversal down the DAG (towards leaves)."""
    # identical, but traverses _out_edges
```

These are **non-breaking additions** to the Phase 8.2 `CausalGraph` spec.

**Additional dunder methods needed on `CausalGraph`**:
- `__contains__(node_id: str) -> bool` — `if node_id not in graph` guard
- `__len__() -> int` — `node_count` for snapshot response

---

## Prometheus metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `explain_api_requests_total` | Counter | `route`, `status` | HTTP request count |
| `explain_api_request_duration_seconds` | Histogram | `route` | Latency distribution |
| `explain_api_rate_limited_total` | Counter | `key_hash` | 429 rejections |
| `explain_api_auth_failures_total` | Counter | — | 401 rejections |
| `explain_api_trace_not_found_total` | Counter | — | 404 on trace lookup |

### PromQL examples

```promql
# Request rate by route
rate(explain_api_requests_total[5m])

# p99 latency
histogram_quantile(0.99,
  rate(explain_api_request_duration_seconds_bucket[5m]))

# Error rate >5% alert
rate(explain_api_requests_total{status=~"4..|5.."}[5m]) /
rate(explain_api_requests_total[5m]) > 0.05

# Sustained rate limiting
increase(explain_api_rate_limited_total[5m]) > 10
```

---

## CognitiveCycle integration

`ExplainApp` runs as a **sidecar** to the main agent process — it does not modify
`CognitiveCycle` at all:

```python
# Launch alongside the cognitive cycle
import asyncio, uvicorn
from asi.phase8.explain_api import build_explain_app

async def main():
    # Build the cognitive subsystems (Phase 8.1 + 8.2)
    tracer = build_decision_tracer(strategy="uniform", buffer_capacity=10_000)
    graph  = build_causal_graph(max_nodes=500, eviction="lru")

    # Wire them into the cycle (Phase 8.1 / 8.2)
    cycle = CognitiveCycle(tracer=tracer, causal_graph=graph, ...)

    # Build the ExplainApp sidecar
    explain_app = build_explain_app(
        tracer=tracer,
        graph=graph,
        api_keys=frozenset(["prod-key-1"]),
        rate_limit_rps=20.0,
    )

    # Run both concurrently
    config = uvicorn.Config(explain_app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await asyncio.gather(cycle.run_forever(), server.serve())
```

Both share the **same `tracer` and `graph` objects** — no IPC, no serialisation overhead.

---

## Test targets (12)

| # | Test | Scenario |
|---|------|----------|
| 1 | `test_health_no_auth` | `/health` returns 200 without key |
| 2 | `test_auth_missing_key` | Missing `X-Api-Key` → 422 |
| 3 | `test_auth_invalid_key` | Wrong key → 401 |
| 4 | `test_traces_empty` | Empty tracer → `items: [], total: 0` |
| 5 | `test_traces_pagination` | `since` + `limit` filtering correct |
| 6 | `test_trace_not_found` | Unknown ID → 404 |
| 7 | `test_trace_explain` | Explain endpoint returns string |
| 8 | `test_graph_snapshot_empty` | Zero-node graph → valid JSON |
| 9 | `test_graph_ancestors_unknown` | Unknown node → 404 |
| 10 | `test_graph_critical_path` | 2-node DAG → correct ordering |
| 11 | `test_rate_limit` | `rate_limit_rps+1` burst → 429 |
| 12 | `test_prometheus_metrics` | All 5 counters/histograms increment |

### Test skeleton

```python
import pytest
from httpx import AsyncClient, ASGITransport
from prometheus_client import CollectorRegistry

@pytest.fixture
def explain_app():
    registry = CollectorRegistry()
    tracer = _make_mock_tracer()
    graph  = _make_mock_graph()
    return build_explain_app(
        tracer=tracer,
        graph=graph,
        api_keys=frozenset(["test-key-1"]),
        rate_limit_rps=100.0,   # high limit for non-rate-limit tests
        registry=registry,
    ), tracer, graph

@pytest.fixture
async def client(explain_app):
    app, tracer, graph = explain_app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c, tracer, graph
```

---

## Implementation order (12 steps)

| Step | Action |
|------|--------|
| 1 | `explain_metrics.py` — pre-init all 5 Prometheus objects |
| 2 | `explain_models.py` — Pydantic v2 response models |
| 3 | `explain_auth.py` — `TokenBucket` (no lock) + `APIKeyAuth` (with lock) |
| 4 | `explain_api.py` — `build_explain_app()`, `/health` route (no auth) |
| 5 | `/metrics` route (`generate_latest()`) |
| 6 | `/traces` + `/traces/{id}` routes wired to `DecisionTracer` |
| 7 | `/traces/{id}/explain` route |
| 8 | `/graph/snapshot` route wired to `CausalGraph` |
| 9 | `/graph/ancestors` + `/graph/descendants` + `/graph/critical-path` |
| 10 | Add `__contains__` + `__len__` to `CausalGraph` (non-breaking) |
| 11 | `mypy --strict` pass; fix type annotations |
| 12 | Full test suite (12 tests, `pytest-asyncio`, `httpx.AsyncClient`) |

---

## Phase 8 roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 8.1 | DecisionTracer | [#276](https://github.com/web3guru888/asi-build/issues/276) | 🟡 In spec |
| 8.2 | CausalGraph | [#280](https://github.com/web3guru888/asi-build/issues/280) | 🟡 In spec |
| **8.3** | **ExplainAPI** | [**#283**](https://github.com/web3guru888/asi-build/issues/283) | **🟡 In spec** |
| 8.4 | Docker / Helm | — | 📋 Planned |
| 8.5 | Sepolia CI | — | 📋 Planned |
