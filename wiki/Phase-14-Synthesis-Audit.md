# Phase 14.5 -- SynthesisAudit: Provenance Tracking and Compliance Ledger

**Phase**: 14.5 of the ASI-Build Autonomous Self-Improvement Loop
**Issue**: [#397](https://github.com/web3guru888/asi-build/issues/397)
**Discussions**: [#398 Show & Tell](https://github.com/web3guru888/asi-build/discussions/398) | [#399 Q&A](https://github.com/web3guru888/asi-build/discussions/399)
**Depends on**: [Phase 14.1 CodeSynthesiser](Phase-14-Code-Synthesiser) | [Phase 14.2 SandboxRunner](Phase-14-Sandbox-Runner) | [Phase 14.3 TestHarness](Phase-14-Test-Harness) | [Phase 14.4 PatchSelector](Phase-14-Patch-Selector)

---

## Motivation

Every patch synthesized by `CodeSynthesiser` and selected by `PatchSelector` must be traceable: *which LLM backend produced it, what strategy was used, which tests passed, when it was applied, and whether it was later reverted*. `SynthesisAudit` provides an **append-only, chain-hashed provenance ledger** that satisfies compliance requirements, supports post-mortem analysis, and feeds long-term learning loops.

---

## `AuditEventType` -- enum

```python
class AuditEventType(str, Enum):
    SYNTHESISED    = "synthesised"     # patch drafted by CodeSynthesiser
    SANDBOX_RUN    = "sandbox_run"     # patch executed in SandboxRunner
    TEST_VERDICT   = "test_verdict"    # verdict from TestHarness
    PATCH_SELECTED = "patch_selected"  # PatchSelector chose this patch
    PATCH_APPLIED  = "patch_applied"   # patch committed to codebase
    PATCH_REVERTED = "patch_reverted"  # patch rolled back after regression
    CYCLE_SUMMARY  = "cycle_summary"   # end-of-cycle aggregate record
```

---

## `AuditRecord` -- frozen dataclass

```python
@dataclass(frozen=True)
class AuditRecord:
    record_id:      str             # uuid4 hex
    event_type:     AuditEventType
    cycle_id:       str             # uuid4 hex -- ties all events in one CognitiveCycle run
    patch_id:       str | None      # links to SynthesisResult.patch_id
    timestamp:      float           # time.time()
    actor:          str             # component name ("CodeSynthesiser", "PatchSelector", ...)
    payload:        dict[str, Any]  # event-specific data (strategy, verdict, score, ...)
    parent_id:      str | None      # record_id of causal predecessor
    schema_version: int = 1
```

---

## `AuditQuery` -- frozen dataclass

```python
@dataclass(frozen=True)
class AuditQuery:
    cycle_id:    str | None = None
    patch_id:    str | None = None
    event_types: tuple[AuditEventType, ...] = ()
    since:       float | None = None   # Unix timestamp lower bound
    until:       float | None = None   # Unix timestamp upper bound
    limit:       int = 200
```

---

## `AuditConfig` -- frozen dataclass

```python
@dataclass(frozen=True)
class AuditConfig:
    backend:               str   = "sqlite"       # "sqlite" | "jsonl" | "memory"
    db_path:               str   = "audit.db"     # for sqlite backend
    jsonl_path:            str   = "audit.jsonl"  # for jsonl backend
    flush_interval_s:      float = 5.0            # async flush cadence
    max_records:           int   = 100_000        # memory backend cap
    enable_integrity_check: bool = True           # SHA-256 chain hash
```

---

## `SynthesisAudit` -- Protocol

```python
@runtime_checkable
class SynthesisAudit(Protocol):
    async def append(self, record: AuditRecord) -> None: ...
    async def query(self, q: AuditQuery) -> list[AuditRecord]: ...
    async def cycle_summary(self, cycle_id: str) -> dict[str, Any]: ...
    async def export_jsonl(self, path: str) -> int: ...       # returns record count
    async def verify_integrity(self) -> bool: ...             # chain hash check
    def stats(self) -> dict[str, int]: ...
```

---

## `SQLiteAudit` -- concrete implementation

### SQLite schema

```sql
CREATE TABLE IF NOT EXISTS audit_records (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id      TEXT NOT NULL UNIQUE,
    event_type     TEXT NOT NULL,
    cycle_id       TEXT NOT NULL,
    patch_id       TEXT,
    timestamp      REAL NOT NULL,
    actor          TEXT NOT NULL,
    payload        TEXT NOT NULL,    -- JSON blob
    parent_id      TEXT,
    schema_version INTEGER NOT NULL DEFAULT 1,
    chain_hash     TEXT              -- SHA-256 chain
);
CREATE INDEX IF NOT EXISTS idx_cycle ON audit_records(cycle_id);
CREATE INDEX IF NOT EXISTS idx_patch ON audit_records(patch_id);
CREATE INDEX IF NOT EXISTS idx_event ON audit_records(event_type);
CREATE INDEX IF NOT EXISTS idx_ts    ON audit_records(timestamp);
```

### `append()` -- non-blocking, chain-hashed

```python
async def append(self, record: AuditRecord) -> None:
    loop = asyncio.get_running_loop()
    start = time.perf_counter()
    row_json = json.dumps(dataclasses.asdict(record), default=str)
    chain_hash: str | None = None
    if self._config.enable_integrity_check:
        chain_hash = hashlib.sha256(
            (self._last_hash + row_json).encode()
        ).hexdigest()
        self._last_hash = chain_hash
    await loop.run_in_executor(None, self._insert_row, record, row_json, chain_hash)
    self._counters[record.event_type] += 1
    ASI_AUDIT_RECORDS.labels(event_type=record.event_type.value).inc()
    ASI_AUDIT_APPEND_LATENCY.observe(time.perf_counter() - start)
```

### `verify_integrity()` -- O(n) chain replay

```python
async def verify_integrity(self) -> bool:
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, self._fetch_all_ordered)
    running_hash = ""
    for row_json, stored_hash in rows:
        expected = hashlib.sha256(
            (running_hash + row_json).encode()
        ).hexdigest()
        if expected != stored_hash:
            ASI_AUDIT_INTEGRITY_FAILURES.inc()
            return False
        running_hash = stored_hash
    return True
```

### `cycle_summary()` -- aggregate view

```python
async def cycle_summary(self, cycle_id: str) -> dict[str, Any]:
    records = await self.query(AuditQuery(cycle_id=cycle_id, limit=10_000))
    counts: dict[str, int] = {}
    applied, reverted = [], []
    pass_rates = []
    for r in records:
        counts[r.event_type.value] = counts.get(r.event_type.value, 0) + 1
        if r.event_type == AuditEventType.PATCH_APPLIED and r.patch_id:
            applied.append(r.patch_id)
        elif r.event_type == AuditEventType.PATCH_REVERTED and r.patch_id:
            reverted.append(r.patch_id)
        elif r.event_type == AuditEventType.TEST_VERDICT:
            pr = r.payload.get("pass_rate")
            if pr is not None:
                pass_rates.append(float(pr))
    return {
        "cycle_id": cycle_id,
        "event_counts": counts,
        "patch_ids_applied": applied,
        "patch_ids_reverted": reverted,
        "aggregate_pass_rate": sum(pass_rates) / len(pass_rates) if pass_rates else None,
    }
```

---

## `AuditFactory` -- backend selection

```python
class AuditFactory:
    @staticmethod
    def create(config: AuditConfig) -> SynthesisAudit:
        match config.backend:
            case "sqlite":  return SQLiteAudit(config)
            case "jsonl":   return JSONLAudit(config)
            case "memory":  return MemoryAudit(config)
            case _:
                raise ValueError(f"Unknown audit backend: {config.backend!r}")
```

---

## Full Phase 14 pipeline with audit overlay

```
CognitiveCycle._synthesis_step()
        |
        | cycle_id = uuid4()
        |
        v
 CodeSynthesiser.synthesise()  ----> AuditRecord(SYNTHESISED)
        |                                  |
        v                                  v
 SandboxRunner.run()           ----> AuditRecord(SANDBOX_RUN)
        |                                  |
        v                                  v
 TestHarness.run_suite()       ----> AuditRecord(TEST_VERDICT)
        |                                  |
        v                                  v
 PatchSelector.select()        ----> AuditRecord(PATCH_SELECTED)
        |                                  |
        v                                  v
 apply / replan                ----> AuditRecord(PATCH_APPLIED | PATCH_REVERTED)
                                           |
                                           v
                                 AuditRecord(CYCLE_SUMMARY)
                                           |
                                           v
                                   SQLiteAudit (chain-hashed)
```

---

## `CognitiveCycle._synthesis_step()` integration

```python
async def _synthesis_step(self) -> None:
    cycle_id = uuid.uuid4().hex
    audit = self._audit  # SynthesisAudit | None

    async def emit(event_type, patch_id, actor, payload, parent_id=None):
        if audit is None:
            return
        await audit.append(AuditRecord(
            record_id=uuid.uuid4().hex,
            event_type=event_type,
            cycle_id=cycle_id,
            patch_id=patch_id,
            timestamp=time.time(),
            actor=actor,
            payload=payload,
            parent_id=parent_id,
        ))

    synth_result = await self._synthesiser.synthesise(request)
    await emit(AuditEventType.SYNTHESISED, synth_result.patch_id,
               "CodeSynthesiser",
               {"strategy": synth_result.strategy.value,
                "tokens": synth_result.token_count})

    exec_result = await self._sandbox.run(ExecutionRequest(...))
    await emit(AuditEventType.SANDBOX_RUN, synth_result.patch_id,
               "SandboxRunner",
               {"exit_code": exec_result.exit_code,
                "wall_s": exec_result.wall_seconds})

    harness_stats = await self._harness.run_suite(test_cases)
    await emit(AuditEventType.TEST_VERDICT, synth_result.patch_id,
               "TestHarness",
               {"pass_rate": harness_stats.pass_rate,
                "fail_count": harness_stats.fail_count})

    selection = await self._selector.select(candidates)
    if selection.winner:
        await emit(AuditEventType.PATCH_SELECTED, selection.winner.patch_id,
                   "PatchSelector",
                   {"strategy": selection.strategy.value,
                    "composite_score": selection.winner_score})
        # apply patch ...
        await emit(AuditEventType.PATCH_APPLIED, selection.winner.patch_id,
                   "CognitiveCycle", {})
    else:
        await self.replan()

    await emit(AuditEventType.CYCLE_SUMMARY, None, "CognitiveCycle",
               {"total_events": 5,
                "pass_rate": harness_stats.pass_rate})
```

---

## `AuditEventType` payload reference

| Event | Payload keys |
|-------|-------------|
| `SYNTHESISED` | `strategy`, `tokens`, `model` |
| `SANDBOX_RUN` | `backend`, `exit_code`, `wall_s`, `memory_mb` |
| `TEST_VERDICT` | `verdict`, `pass_rate`, `fail_count`, `error_count` |
| `PATCH_SELECTED` | `strategy`, `composite_score`, `winner_patch_id` |
| `PATCH_APPLIED` | `patch_id`, `applied_at` |
| `PATCH_REVERTED` | `patch_id`, `reason` |
| `CYCLE_SUMMARY` | `total_events`, `pass_rate`, `duration_s` |

---

## Backend selection guide

| Backend | Best for | Query | Chain hash | Notes |
|---------|----------|-------|------------|-------|
| `sqlite` | Production | Yes | Yes | Requires executor |
| `jsonl` | Dev / log shipping | No | No | grep-friendly |
| `memory` | Unit tests | Yes | No | Lost on restart |

---

## Prometheus metrics

| Metric | Type | Labels |
|--------|------|--------|
| `asi_audit_records_total` | Counter | `event_type` |
| `asi_audit_append_latency_seconds` | Histogram | -- |
| `asi_audit_query_latency_seconds` | Histogram | -- |
| `asi_audit_integrity_failures_total` | Counter | -- |
| `asi_audit_db_size_bytes` | Gauge | -- |

### PromQL examples

```promql
# Append rate by event type
rate(asi_audit_records_total[5m])

# p95 append latency
histogram_quantile(0.95, rate(asi_audit_append_latency_seconds_bucket[5m]))

# Alert: integrity failure
ALERT SynthesisAuditIntegrityFailure
  IF increase(asi_audit_integrity_failures_total[5m]) > 0
  LABELS { severity="critical" }
  ANNOTATIONS { summary="Audit chain hash mismatch -- possible record tampering" }
```

### Grafana dashboard YAML

```yaml
panels:
  - title: "Audit Records / min by event_type"
    type: timeseries
    expr: rate(asi_audit_records_total[1m]) * 60

  - title: "Append latency p95 (ms)"
    type: timeseries
    expr: histogram_quantile(0.95, rate(asi_audit_append_latency_seconds_bucket[5m])) * 1000

  - title: "Integrity failures"
    type: stat
    expr: asi_audit_integrity_failures_total

  - title: "Audit DB size (MB)"
    type: gauge
    expr: asi_audit_db_size_bytes / 1024 / 1024
```

---

## mypy `--strict` surface

| Symbol | Status |
|--------|--------|
| `AuditEventType` | `str, Enum` |
| `AuditRecord` | `frozen=True`, all fields typed |
| `AuditQuery` | `frozen=True`, defaults typed |
| `AuditConfig` | `frozen=True` |
| `SynthesisAudit` | `@runtime_checkable Protocol` |
| `SQLiteAudit` | explicit return types |
| `payload: dict[str, Any]` | `from __future__ import annotations` |

---

## Test targets (12)

1. `test_audit_record_frozen` -- mutation raises `FrozenInstanceError`
2. `test_append_and_query_by_cycle_id`
3. `test_query_by_event_type_filter`
4. `test_query_time_range`
5. `test_query_limit_respected`
6. `test_cycle_summary_counts`
7. `test_cycle_summary_pass_rate`
8. `test_export_jsonl_roundtrip`
9. `test_verify_integrity_valid_chain`
10. `test_verify_integrity_tampered_record`
11. `test_sqlite_backend_concurrent_appends` -- asyncio.gather 50 tasks
12. `test_cognitive_cycle_audit_integration` -- mock all Phase 14 components, assert all 5+ AuditEventType variants appended

---

## Implementation order (14 steps)

1. `AuditEventType` enum (7 values)
2. `AuditRecord` frozen dataclass
3. `AuditQuery` frozen dataclass
4. `AuditConfig` frozen dataclass
5. `SynthesisAudit` Protocol (`@runtime_checkable`)
6. SQLite schema (`CREATE TABLE` + indexes)
7. `SQLiteAudit.append()` + chain hash + executor
8. `SQLiteAudit.query()` parameterized SQL
9. `SQLiteAudit.cycle_summary()`
10. `SQLiteAudit.export_jsonl()`
11. `SQLiteAudit.verify_integrity()` chain replay
12. `JSONLAudit` (no chain hash, streaming append)
13. `MemoryAudit` (in-process list, fast tests)
14. `CognitiveCycle._synthesis_step()` -- inject audit, emit 5+ events per cycle

---

## Phase 14 roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 14.1 | CodeSynthesiser | [#385](https://github.com/web3guru888/asi-build/issues/385) | spec ready |
| 14.2 | SandboxRunner | [#388](https://github.com/web3guru888/asi-build/issues/388) | spec ready |
| 14.3 | TestHarness | [#391](https://github.com/web3guru888/asi-build/issues/391) | spec ready |
| 14.4 | PatchSelector | [#394](https://github.com/web3guru888/asi-build/issues/394) | spec ready |
| **14.5** | **SynthesisAudit** | [**#397**](https://github.com/web3guru888/asi-build/issues/397) | **spec ready** |

---

## Phase 14 integration table

| Component | Provides to SynthesisAudit | Receives from SynthesisAudit |
|-----------|---------------------------|------------------------------|
| CodeSynthesiser | `SynthesisResult.patch_id`, strategy | `SYNTHESISED` event recorded |
| SandboxRunner | `ExecutionResult.exit_code`, wall_s | `SANDBOX_RUN` event recorded |
| TestHarness | `HarnessStats.pass_rate`, verdicts | `TEST_VERDICT` event recorded |
| PatchSelector | `SelectionResult.winner`, score | `PATCH_SELECTED` event recorded |
| CognitiveCycle | `cycle_id`, apply/revert signal | `PATCH_APPLIED`/`PATCH_REVERTED`/`CYCLE_SUMMARY` events |

---

*Phase 14 is the Autonomous Self-Improvement Loop. Phase 14.5 `SynthesisAudit` is the final sub-phase, completing the full provenance chain for every code synthesis cycle.*
