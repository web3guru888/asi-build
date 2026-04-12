# Phase 6 Fisher Backends: Neo4jFisherStore and CachedFisherStore

**Status**: Specification (Issue #245)  
**Phase**: 6.2  
**Depends on**: [Phase-6-EWC-Foundation](Phase-6-EWC-Foundation) (Phase 6.1)

---

## Overview

Phase 6.1 introduced `InMemoryFisherStore` — sufficient for development and testing, but Fisher matrices are lost on process restart. Phase 6.2 adds two production-grade backends:

- **`Neo4jFisherStore`**: Persists Fisher matrices in the existing Neo4j knowledge graph via UNWIND batch writes.
- **`CachedFisherStore`**: Wraps any `FisherMatrixBase` backend with a Redis TTL cache.

Both implement the `FisherMatrixBase` ABC and are assembled by `FisherStoreFactory` based on `EWCConfig`.

---

## Architecture

```
FisherMatrixBase (ABC)
├── InMemoryFisherStore          ← Phase 6.1
├── Neo4jFisherStore             ← Phase 6.2
└── CachedFisherStore            ← Phase 6.2
      └── wraps: FisherMatrixBase (any)

FisherStoreFactory.build(config, neo4j_driver?, redis_client?)
  → FisherMatrixBase
```

---

## Neo4jFisherStore

### Neo4j Schema

```cypher
// Store matrix — single UNWIND round-trip
UNWIND $rows AS row
MERGE (p:Parameter {name: row.name})
MERGE (t:Task {id: row.task_id})
CREATE (p)-[:HAS_FISHER {
  value: row.value,
  computed_at: datetime($computed_at)
}]->(t)

// Load matrix — reconstruct FisherSnapshot
MATCH (p:Parameter)-[f:HAS_FISHER]->(t:Task {id: $task_id})
RETURN p.name AS name, f.value AS value
ORDER BY p.name

// List stored tasks
MATCH ()-[f:HAS_FISHER]->(t:Task)
RETURN DISTINCT t.id AS task_id
ORDER BY task_id
```

### Class Skeleton

```python
STORE_CYPHER = """
UNWIND $rows AS row
MERGE (p:Parameter {name: row.name})
MERGE (t:Task {id: row.task_id})
CREATE (p)-[:HAS_FISHER {value: row.value, computed_at: datetime($computed_at)}]->(t)
"""

LOAD_CYPHER = """
MATCH (p:Parameter)-[f:HAS_FISHER]->(t:Task {id: $task_id})
RETURN p.name AS name, f.value AS value
ORDER BY p.name
"""

class Neo4jFisherStore(FisherMatrixBase):
    def __init__(self, driver: AsyncDriver, db: str = "neo4j") -> None:
        self._driver = driver
        self._db = db

    async def store_matrix(self, task_id: str, snapshot: FisherSnapshot) -> None:
        rows = [
            {"name": name, "task_id": task_id, "value": float(val)}
            for name, val in snapshot.fisher_diag.items()
        ]
        async with self._driver.session(database=self._db) as session:
            await session.run(
                STORE_CYPHER,
                rows=rows,
                computed_at=snapshot.computed_at.isoformat(),
            )

    async def load_matrix(self, task_id: str) -> FisherSnapshot | None:
        async with self._driver.session(database=self._db) as session:
            result = await session.run(LOAD_CYPHER, task_id=task_id)
            records = await result.data()
        if not records:
            return None
        fisher_diag = {r["name"]: r["value"] for r in records}
        return FisherSnapshot(
            task_id=task_id,
            fisher_diag=fisher_diag,
            computed_at=datetime.utcnow(),  # approximate
        )

    async def list_tasks(self) -> list[str]:
        async with self._driver.session(database=self._db) as session:
            result = await session.run(
                "MATCH ()-[f:HAS_FISHER]->(t:Task) RETURN DISTINCT t.id AS task_id ORDER BY task_id"
            )
            records = await result.data()
        return [r["task_id"] for r in records]
```

### Write Latency Reference

| Parameters | Write time (Neo4j 5.x local) |
|-----------|------------------------------|
| 1 K | ~8 ms |
| 10 K | ~35 ms |
| 50 K | ~80 ms |
| 100 K | ~160 ms |
| 500 K | ~450 ms (chunk at >100K) |

All within the SLEEP_PHASE budget (~500ms).

---

## CachedFisherStore

### Prometheus Counters

```python
FISHER_CACHE_HITS = Counter(
    "ewc_fisher_cache_hits_total",
    "Redis cache hits on Fisher matrix load",
)
FISHER_CACHE_MISSES = Counter(
    "ewc_fisher_cache_misses_total",
    "Redis cache misses on Fisher matrix load",
)
```

### Class Skeleton

```python
class CachedFisherStore(FisherMatrixBase):
    KEY_PREFIX = "fisher"

    def __init__(
        self, backend: FisherMatrixBase, redis: Redis, ttl: int = 3600
    ) -> None:
        self._backend = backend
        self._redis = redis
        self._ttl = ttl

    def _key(self, task_id: str) -> str:
        return f"{self.KEY_PREFIX}:{task_id}"

    async def store_matrix(self, task_id: str, snapshot: FisherSnapshot) -> None:
        await self._backend.store_matrix(task_id, snapshot)
        # Populate cache immediately after write
        await self._redis.setex(
            self._key(task_id), self._ttl, snapshot.model_dump_json()
        )

    async def load_matrix(self, task_id: str) -> FisherSnapshot | None:
        if cached := await self._redis.get(self._key(task_id)):
            FISHER_CACHE_HITS.inc()
            return FisherSnapshot.model_validate_json(cached)
        FISHER_CACHE_MISSES.inc()
        snapshot = await self._backend.load_matrix(task_id)
        if snapshot:
            await self._redis.setex(
                self._key(task_id), self._ttl, snapshot.model_dump_json()
            )
        return snapshot

    async def list_tasks(self) -> list[str]:
        return await self._backend.list_tasks()
```

---

## FisherStoreFactory

```python
class FisherStoreFactory:
    @staticmethod
    def build(
        config: EWCConfig,
        neo4j_driver: AsyncDriver | None = None,
        redis_client: Redis | None = None,
    ) -> FisherMatrixBase:
        match config.fisher_backend:
            case "in_memory":
                return InMemoryFisherStore()
            case "neo4j":
                assert neo4j_driver, "neo4j_driver required"
                return Neo4jFisherStore(neo4j_driver, config.neo4j_db)
            case "cached_neo4j":
                assert neo4j_driver and redis_client, "both required"
                base = Neo4jFisherStore(neo4j_driver, config.neo4j_db)
                return CachedFisherStore(base, redis_client, config.redis_ttl)
            case _:
                raise ValueError(f"Unknown fisher_backend: {config.fisher_backend!r}")
```

---

## Test Targets

| # | Test | Scope |
|---|------|-------|
| 1 | `test_neo4j_store_roundtrip` | store → load → assert dict equal |
| 2 | `test_unwind_single_round_trip` | `session.run` called exactly once |
| 3 | `test_load_missing_task_returns_none` | missing task_id → None |
| 4 | `test_list_tasks_sorted` | 3 tasks → sorted list |
| 5 | `test_cached_store_hit_path` | Redis returns bytes → skip Neo4j |
| 6 | `test_cached_store_miss_path` | Redis returns None → Neo4j called |
| 7 | `test_cache_hit_counter_incremented` | FISHER_CACHE_HITS +1 |
| 8 | `test_cache_miss_counter_incremented` | FISHER_CACHE_MISSES +1 |
| 9 | `test_factory_in_memory` | → InMemoryFisherStore |
| 10 | `test_factory_neo4j` | → Neo4jFisherStore |
| 11 | `test_factory_cached_neo4j` | → CachedFisherStore |
| 12 | `test_concurrent_store_load` | asyncio.gather(5 concurrent loads) |

---

## Redis Key Convention

| Key pattern | Value | TTL |
|-------------|-------|-----|
| `fisher:{task_id}` | JSON-serialised `FisherSnapshot` | 3600s (configurable) |

Other ASI-Build Redis namespaces: `phero:*` (pheromones), `bb:*` (Blackboard).

---

## Error Handling

If Neo4j write fails during SLEEP_PHASE:
1. Catch exception, log to Blackboard: `blackboard.set("ewc.last_store_error", str(e))`
2. Increment `ewc_store_errors_total` Prometheus counter
3. **Do not raise** — SLEEP_PHASE must complete regardless

---

## Phase 6 Roadmap

| Sub-phase | Scope |
|-----------|-------|
| **6.1** | FisherMatrixBase ABC, InMemoryFisherStore, EWCConfig, EWCRegulariser, SLEEP hook (#241) |
| **6.2** | Neo4jFisherStore, CachedFisherStore, FisherStoreFactory (#245) |
| **6.3** | EWCRegulariser × STDPOnlineLearner integration (TBD) |
| **6.4** | Phase 6 CI harness + Grafana EWC dashboard panel (TBD) |

See also: [Phase-6-EWC-Foundation](Phase-6-EWC-Foundation) · [Phase-5-Online-Learning](Phase-5-Online-Learning) · Issue #241 · Issue #245

