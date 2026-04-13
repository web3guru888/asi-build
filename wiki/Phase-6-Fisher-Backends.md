# Phase 6.2 — Fisher Information Backends: Neo4j, Redis Cache, and FisherStoreFactory

**Status**: 🟡 In Progress — Issue #245  
**Depends on**: Phase-6-EWC-Foundation (Phase 6.1, Issue #241)  
**Previous**: [Phase-6-EWC-Foundation](Phase-6-EWC-Foundation)  
**Next**: [Phase-6-EWC-Integration](Phase-6-EWC-Integration) (Phase 6.3, Issue #249)

---

## Overview

Phase 6.2 adds **persistent and cached Fisher information storage backends** to the EWC continual-learning system. The `InMemoryFisherStore` from Phase 6.1 is sufficient for single-run development but cannot share Fisher data across agents or survive process restarts. Phase 6.2 delivers:

1. **`Neo4jFisherStore`** — durable persistence via the existing Neo4j knowledge graph
2. **`CachedFisherStore`** — Redis-backed TTL cache layered over any backend
3. **`FisherStoreFactory`** — configuration-driven backend selection

---

## Architecture

```
EWCRegulariser
      │
      ▼
FisherMatrixBase (ABC, Phase 6.1)
      │
      ├── InMemoryFisherStore   ← dev / unit tests
      │
      ├── Neo4jFisherStore      ← production (durable, shared)
      │       │
      └── CachedFisherStore ───►│  (wraps Neo4j with Redis TTL cache)
              │
              ▼
          Redis (TTL = 300s default)
```

**FisherStoreFactory** selects the backend at startup:

```python
store = FisherStoreFactory.from_config(ewc_config)
# ewc_config.fisher_backend = "in_memory" | "neo4j" | "cached_neo4j"
```

---

## Components

### Neo4jFisherStore

**File**: `asi/phase6/learning/fisher_neo4j.py`

```python
class Neo4jFisherStore(FisherMatrixBase):
    """Persist FisherSnapshots to Neo4j as FisherMatrix nodes."""

    async def save(self, task_id: str, snapshot: FisherSnapshot) -> None:
        async with self._driver.session() as session:
            await session.execute_write(self._write_snapshot, task_id, snapshot)

    async def load(self, task_id: str) -> FisherSnapshot | None:
        async with self._driver.session() as session:
            return await session.execute_read(self._read_snapshot, task_id)

    @staticmethod
    async def _write_snapshot(tx, task_id: str, snapshot: FisherSnapshot) -> None:
        await tx.run(
            """
            MERGE (f:FisherMatrix {task_id: $task_id})
            SET f.fisher_diag    = $fisher_diag,
                f.anchor_weights = $anchor_weights,
                f.episode_count  = $episode_count,
                f.updated_at     = datetime()
            """,
            task_id=task_id,
            fisher_diag=snapshot.fisher_diag.tolist(),
            anchor_weights=snapshot.anchor_weights.tolist(),
            episode_count=snapshot.episode_count,
        )
```

#### Neo4j Schema

```cypher
CREATE CONSTRAINT fisher_task_unique IF NOT EXISTS
  FOR (f:FisherMatrix) REQUIRE f.task_id IS UNIQUE;

CREATE INDEX fisher_updated_idx IF NOT EXISTS
  FOR (f:FisherMatrix) ON (f.updated_at);
```

Node structure:
```
(:FisherMatrix {
  task_id:        "agent-7f3a:navigation",
  fisher_diag:    [0.12, 0.03, 0.87, ...],   // float list, len = weight_dim
  anchor_weights: [0.45, -0.12, 0.33, ...],  // float list, len = weight_dim
  episode_count:  42,
  updated_at:     datetime
})
```

#### Latency Characteristics

| Operation | Typical latency | Notes |
|---|---|---|
| `save()` | 8–25 ms | MERGE + SET on indexed node |
| `load()` | 5–15 ms | Single node lookup by task_id |
| First write | 15–40 ms | Index warm-up |
| Bulk UNWIND (Phase 6.4) | 2–5 ms per snapshot | For batch snapshot updates |

---

### CachedFisherStore

**File**: `asi/phase6/learning/fisher_cache.py`

```python
class CachedFisherStore(FisherMatrixBase):
    """Redis TTL cache wrapping any FisherMatrixBase backend."""

    KEY_PREFIX = "fisher:"
    DEFAULT_TTL = 300  # seconds

    async def load(self, task_id: str) -> FisherSnapshot | None:
        key = f"{self.KEY_PREFIX}{task_id}"
        cached = await self._redis.get(key)
        if cached is not None:
            CACHE_HIT.labels(task_id=task_id).inc()
            return FisherSnapshot.from_bytes(cached)
        CACHE_MISS.labels(task_id=task_id).inc()
        snapshot = await self._backend.load(task_id)
        if snapshot is not None:
            await self._redis.setex(key, self._ttl, snapshot.to_bytes())
        return snapshot

    async def save(self, task_id: str, snapshot: FisherSnapshot) -> None:
        await self._backend.save(task_id, snapshot)
        key = f"{self.KEY_PREFIX}{task_id}"
        await self._redis.setex(key, self._ttl, snapshot.to_bytes())
```

#### Prometheus Metrics

| Metric | Type | Labels |
|---|---|---|
| `phase6_fisher_cache_hit_total` | Counter | `task_id` |
| `phase6_fisher_cache_miss_total` | Counter | `task_id` |
| `phase6_fisher_cache_write_total` | Counter | `task_id` |

#### Redis Key Convention

All Fisher keys use the `fisher:` namespace prefix:
```
fisher:{task_id}    →  serialized FisherSnapshot (msgpack)
fisher:agent-7f3a:navigation  →  TTL=300s
```

This allows bulk invalidation: `redis-cli --scan --pattern 'fisher:*' | xargs redis-cli del`

---

### FisherStoreFactory

**File**: `asi/phase6/learning/fisher_factory.py`

```python
class FisherStoreFactory:
    """Select and construct a FisherMatrixBase implementation from EWCConfig."""

    _REGISTRY: dict[str, type[FisherMatrixBase]] = {
        "in_memory":    InMemoryFisherStore,
        "neo4j":        Neo4jFisherStore,
        "cached_neo4j": CachedFisherStore,
    }

    @classmethod
    def from_config(cls, config: EWCConfig) -> FisherMatrixBase:
        backend_cls = cls._REGISTRY.get(config.fisher_backend)
        if backend_cls is None:
            raise ValueError(
                f"Unknown Fisher backend: {config.fisher_backend!r}. "
                f"Valid options: {list(cls._REGISTRY)}"
            )
        match config.fisher_backend:
            case "in_memory":
                return InMemoryFisherStore(max_snapshots=config.max_fisher_snapshots)
            case "neo4j":
                return Neo4jFisherStore(driver=config.neo4j_driver)
            case "cached_neo4j":
                neo4j = Neo4jFisherStore(driver=config.neo4j_driver)
                return CachedFisherStore(
                    backend=neo4j,
                    redis=config.redis_client,
                    ttl=config.fisher_cache_ttl,
                )
```

---

## EWCConfig — New Fields (Phase 6.2)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `fisher_backend` | `Literal["in_memory", "neo4j", "cached_neo4j"]` | `"in_memory"` | Backend selector |
| `neo4j_driver` | `AsyncDriver \| None` | `None` | Required for neo4j/cached_neo4j |
| `redis_client` | `Redis \| None` | `None` | Required for cached_neo4j |
| `fisher_cache_ttl` | `int` | `300` | Redis TTL in seconds |
| `max_fisher_snapshots` | `int` | `100` | InMemoryFisherStore bound |

---

## Test Targets (12)

| Test | Backend | What it verifies |
|---|---|---|
| `test_neo4j_save_and_load` | Neo4j | Round-trip FisherSnapshot → Neo4j → back |
| `test_neo4j_missing_task_id` | Neo4j | Returns None for unknown task_id |
| `test_neo4j_overwrite` | Neo4j | MERGE updates existing node (no duplicate) |
| `test_neo4j_shape_preserved` | Neo4j | Array shapes match after list→ndarray conversion |
| `test_cache_hit_path` | Cached | Redis hit → no backend call → cache_hit counter |
| `test_cache_miss_path` | Cached | Redis miss → backend call → populates cache |
| `test_cache_save_writes_both` | Cached | save() writes backend AND Redis |
| `test_cache_ttl_expiry` | Cached | After TTL, next load hits backend (mock time) |
| `test_factory_in_memory` | Factory | Returns InMemoryFisherStore |
| `test_factory_neo4j` | Factory | Returns Neo4jFisherStore with driver |
| `test_factory_cached_neo4j` | Factory | Returns CachedFisherStore wrapping Neo4j |
| `test_factory_unknown_backend` | Factory | Raises ValueError with helpful message |

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Neo4j unavailable on `load()` | Propagate `ServiceUnavailable`; caller gets None via try/except in EWCRegulariser |
| Neo4j unavailable on `save()` | Log error + increment `phase6_fisher_save_error_total`; don't crash SLEEP_PHASE |
| Redis unavailable on `load()` | Fall through to backend (degraded mode, no cache) |
| Redis unavailable on `save()` | Log warning; data is still in Neo4j |
| Snapshot shape mismatch | Log warning + return None; caller uses zero gradient |

---

## Phase 6 Roadmap

| Phase | Issue | Status |
|---|---|---|
| 6.1 — EWC Foundation | #241 | 🟡 Open |
| 6.2 — Fisher Backends | #245 | 🟡 Open |
| 6.3 — EWC Integration | #249 | 🟡 Open |
| 6.4 — Fisher warm-up + task registry | TBD | 📋 Planned |

---

*See also: [Phase-6-EWC-Foundation](Phase-6-EWC-Foundation) · [Phase-6-EWC-Integration](Phase-6-EWC-Integration) · Issue #245 · Discussion #247*
