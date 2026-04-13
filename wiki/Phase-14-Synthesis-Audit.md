# Phase 14 — Synthesis Audit

> **Status**: 🟡 Spec open — Issue [#397](https://github.com/web3guru888/asi-build/issues/397)
> **Phase**: 14.5 of 14 in the Autonomous Code Synthesis pipeline
> **Depends on**: [CodeSynthesiser](Phase-14-Code-Synthesiser) · [PatchSelector](Phase-14-Patch-Selector)
> **Discussions**: [Show & Tell #398](https://github.com/web3guru888/asi-build/discussions/398) · [Q&A #399](https://github.com/web3guru888/asi-build/discussions/399)

---

## Overview

`SynthesisAudit` is the **provenance ledger** for the Phase 14 autonomous synthesis pipeline. Every patch drafted by `CodeSynthesiser`, executed by `SandboxRunner`, evaluated by `TestHarness`, and selected by `PatchSelector` is logged as an immutable `AuditRecord`. The ledger supports post-mortem analysis, compliance requirements, and long-term learning loops.

---

## Data Model

### `AuditEventType` — enum

```python
class AuditEventType(str, Enum):
    SYNTHESISED    = "synthesised"      # patch drafted by CodeSynthesiser
    SANDBOX_RUN    = "sandbox_run"      # executed in SandboxRunner
    TEST_VERDICT   = "test_verdict"     # verdict from TestHarness
    PATCH_SELECTED = "patch_selected"   # PatchSelector chose this patch
    PATCH_APPLIED  = "patch_applied"    # committed to the codebase
    PATCH_REVERTED = "patch_reverted"   # rolled back after regression
    CYCLE_SUMMARY  = "cycle_summary"    # end-of-cycle aggregate
```

### `AuditRecord` — frozen dataclass

```python
@dataclass(frozen=True)
class AuditRecord:
    record_id:      str            # uuid4 hex — globally unique
    event_type:     AuditEventType
    cycle_id:       str            # ties all events in one CognitiveCycle run
    patch_id:       str | None     # links to SynthesisResult.patch_id
    timestamp:      float          # time.time()
    actor:          str            # "CodeSynthesiser" | "SandboxRunner" | ...
    payload:        dict[str, Any] # event-specific data
    parent_id:      str | None     # causal predecessor record_id
    schema_version: int = 1
```

### `AuditQuery` — frozen dataclass

```python
@dataclass(frozen=True)
class AuditQuery:
    cycle_id:   str | None         = None
    patch_id:   str | None         = None
    event_type: AuditEventType | None = None
    since:      float | None       = None
    until:      float | None       = None
    limit:      int                = 100
```

### `AuditConfig` — frozen dataclass

```python
@dataclass(frozen=True)
class AuditConfig:
    backend:      str   = "sqlite"  # "sqlite" | "jsonl" | "memory"
    db_path:      str   = "synthesis_audit.db"
    jsonl_path:   str   = "synthesis_audit.jsonl"
    flush_every:  int   = 10        # background flush interval (seconds)
    verify_chain: bool  = True      # enable chain hash validation
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SynthesisAudit(Protocol):
    async def append(self, record: AuditRecord) -> None: ...
    async def query(self, q: AuditQuery) -> list[AuditRecord]: ...
    async def cycle_summary(self, cycle_id: str) -> dict[str, Any]: ...
    async def export_jsonl(self, path: str) -> int: ...          # returns record count
    async def verify_integrity(self) -> bool: ...                # chain hash check
    def stats(self) -> dict[str, int]: ...
```

---

## SQLite Backend — `SQLiteAudit`

### Schema

```sql
CREATE TABLE IF NOT EXISTS audit_records (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id      TEXT    NOT NULL UNIQUE,
    event_type     TEXT    NOT NULL,
    cycle_id       TEXT    NOT NULL,
    patch_id       TEXT,
    timestamp      REAL    NOT NULL,
    actor          TEXT    NOT NULL,
    payload        TEXT    NOT NULL,   -- JSON
    parent_id      TEXT,
    schema_version INTEGER NOT NULL DEFAULT 1,
    chain_hash     TEXT               -- SHA-256(prev_hash || record_json)
);
CREATE INDEX IF NOT EXISTS idx_cycle ON audit_records(cycle_id);
CREATE INDEX IF NOT EXISTS idx_patch ON audit_records(patch_id);
```

### Chain Hash

Each record stores `chain_hash = sha256(prev_hash + json(record))`. `verify_integrity()` replays the chain and detects any tampering.

### `append()` — non-blocking

```python
async def append(self, record: AuditRecord) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, self._sync_append, record)
```

---

## Data Flow in `CognitiveCycle._synthesis_step()`

```
CognitiveCycle._synthesis_step(task, audit)
  │
  ├─ synthesise()        → AuditRecord(SYNTHESISED)      → audit.append()
  ├─ sandbox.run()       → AuditRecord(SANDBOX_RUN)      → audit.append()
  ├─ harness.run_suite() → AuditRecord(TEST_VERDICT)     → audit.append()
  ├─ selector.select()   → AuditRecord(PATCH_SELECTED)   → audit.append()
  └─ (apply/replan)      → AuditRecord(CYCLE_SUMMARY)    → audit.append()
```

### Integration Snippet

```python
async def _synthesis_step(
    self,
    task: Task,
    audit: SynthesisAudit,
) -> SynthesisResult | None:
    cycle_id = uuid.uuid4().hex

    result = await self._synthesiser.synthesise(task)
    await audit.append(AuditRecord(
        record_id=uuid.uuid4().hex, event_type=AuditEventType.SYNTHESISED,
        cycle_id=cycle_id, patch_id=result.patch_id, timestamp=time.time(),
        actor="CodeSynthesiser", payload={"strategy": result.strategy.value},
        parent_id=None,
    ))

    exec_result = await self._sandbox.run(result)
    await audit.append(AuditRecord(
        record_id=uuid.uuid4().hex, event_type=AuditEventType.SANDBOX_RUN,
        cycle_id=cycle_id, patch_id=result.patch_id, timestamp=time.time(),
        actor="SandboxRunner", payload={"returncode": exec_result.returncode},
        parent_id=None,
    ))

    stats = await self._harness.run_suite([result], self._harness_cfg)
    await audit.append(AuditRecord(
        record_id=uuid.uuid4().hex, event_type=AuditEventType.TEST_VERDICT,
        cycle_id=cycle_id, patch_id=result.patch_id, timestamp=time.time(),
        actor="TestHarness", payload={"pass_rate": stats.pass_rate},
        parent_id=None,
    ))

    selection = await self._selector.select([result], self._selector_cfg)
    await audit.append(AuditRecord(
        record_id=uuid.uuid4().hex, event_type=AuditEventType.PATCH_SELECTED,
        cycle_id=cycle_id, patch_id=getattr(selection.winner, "patch_id", None),
        timestamp=time.time(), actor="PatchSelector",
        payload={"strategy": self._selector_cfg.strategy.value,
                 "score": selection.winner_score},
        parent_id=None,
    ))

    await audit.append(AuditRecord(
        record_id=uuid.uuid4().hex, event_type=AuditEventType.CYCLE_SUMMARY,
        cycle_id=cycle_id, patch_id=None, timestamp=time.time(),
        actor="CognitiveCycle",
        payload={"winner": selection.winner is not None,
                 "pass_rate": stats.pass_rate},
        parent_id=None,
    ))

    return selection.winner
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_audit_records_total` | Counter | `event_type` | Records appended |
| `asi_audit_append_latency_seconds` | Histogram | — | `append()` latency |
| `asi_audit_query_latency_seconds` | Histogram | — | `query()` latency |
| `asi_audit_integrity_failures_total` | Counter | — | Chain hash mismatches |
| `asi_audit_db_size_bytes` | Gauge | — | SQLite file size (polled) |

### PromQL Queries

```promql
# Records per event type (1-min rate)
rate(asi_audit_records_total[1m])

# Integrity failure alert
increase(asi_audit_integrity_failures_total[5m]) > 0

# Append latency P99
histogram_quantile(0.99, rate(asi_audit_append_latency_seconds_bucket[5m]))
```

### Grafana Alert — Integrity Failure

```yaml
- alert: SynthesisAuditIntegrityFailure
  expr: increase(asi_audit_integrity_failures_total[5m]) > 0
  for: 0m
  labels:
    severity: critical
  annotations:
    summary: "SynthesisAudit chain hash mismatch detected — potential tampering"
```

---

## mypy --strict Compliance

| Class | `--strict` notes |
|-------|-----------------|
| `AuditRecord` | `payload: dict[str, Any]` requires `from __future__ import annotations` |
| `SQLiteAudit.append` | `run_in_executor` typed as `asyncio.AbstractEventLoop.run_in_executor` |
| `SynthesisAudit` Protocol | `@runtime_checkable` — no `__init__` signature needed |
| `AuditConfig.backend` | Literal`["sqlite", "jsonl", "memory"]` preferred over `str` |

---

## Test Targets (12)

| # | Test | Key assertion |
|---|------|---------------|
| 1 | `test_audit_record_frozen` | `FrozenInstanceError` on mutation |
| 2 | `test_append_and_query_by_cycle_id` | round-trip |
| 3 | `test_query_by_event_type_filter` | only matching types returned |
| 4 | `test_query_time_range` | `since`/`until` respected |
| 5 | `test_query_limit_respected` | at most `limit` records |
| 6 | `test_cycle_summary_counts` | event counts match |
| 7 | `test_cycle_summary_pass_rate` | aggregated from TEST_VERDICT payload |
| 8 | `test_export_jsonl_roundtrip` | JSON-L can be re-imported |
| 9 | `test_verify_integrity_valid_chain` | returns `True` |
| 10 | `test_verify_integrity_tampered_record` | returns `False` |
| 11 | `test_sqlite_backend_concurrent_appends` | `asyncio.gather` 50 tasks |
| 12 | `test_cognitive_cycle_audit_integration` | all 5 event types appended |

---

## Implementation Order (14 steps)

1. `AuditEventType` enum
2. `AuditRecord` frozen dataclass
3. `AuditQuery` frozen dataclass
4. `AuditConfig` frozen dataclass
5. `SynthesisAudit` Protocol + `@runtime_checkable`
6. SQLite schema (`CREATE TABLE IF NOT EXISTS`)
7. `SQLiteAudit.append()` + chain hash
8. `SQLiteAudit.query()` parameterized SQL
9. `SQLiteAudit.cycle_summary()`
10. `SQLiteAudit.export_jsonl()`
11. `SQLiteAudit.verify_integrity()`
12. `SQLiteAudit._flush_loop()` background task
13. `MemoryAudit` (tests) + `JSONLAudit` (lightweight)
14. `CognitiveCycle._synthesis_step()` audit injection (5 append() calls)

---

## Phase 14 Roadmap — Final Status

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 14.1 | CodeSynthesiser | [#385](https://github.com/web3guru888/asi-build/issues/385) | 🟡 Spec open |
| 14.2 | SandboxRunner | [#388](https://github.com/web3guru888/asi-build/issues/388) | 🟡 Spec open |
| 14.3 | TestHarness | [#391](https://github.com/web3guru888/asi-build/issues/391) | 🟡 Spec open |
| 14.4 | PatchSelector | [#394](https://github.com/web3guru888/asi-build/issues/394) | 🟡 Spec open |
| 14.5 | SynthesisAudit | [#397](https://github.com/web3guru888/asi-build/issues/397) | 🟡 Spec open |

**Next**: Phase 15 — Runtime Self-Modification & Hot-Reload → [#400](https://github.com/web3guru888/asi-build/discussions/400)

---

## Phase 14→15 Integration

| Producer (Phase 14) | Consumer (Phase 15) | Data |
|---------------------|---------------------|------|
| `SynthesisAudit` records | `RollbackManager` (15.4) | `PATCH_APPLIED`/`PATCH_REVERTED` events |
| `cycle_summary()` | `ModuleRegistry` (15.1) | cycle success/failure metadata |
| `verify_integrity()` | Safety dashboard | compliance assertion |

