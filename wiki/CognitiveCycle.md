# Cognitive Cycle

**Status**: Design Phase 🏗️  
**Tracking**: [Issue #39](https://github.com/web3guru888/asi-build/issues/39) — Design CognitiveCycle: a full-system perception-to-action loop  
**Discussion**: [#40 — Show & Tell: Designing the CognitiveCycle](https://github.com/web3guru888/asi-build/discussions/40)

---

## Overview

The `CognitiveCycle` is ASI:BUILD's answer to a fundamental question: **how do 29 heterogeneous modules run together as a coherent, real-time intelligence system?**

Each module has its own tests and internal logic, but nothing currently sequences them into a unified perception-action loop. The `CognitiveCycle` class fills that gap.

Design goals:
1. **Temporal coordination** — all modules share a common tick
2. **Priority ordering** — sensory input always before reasoning, safety always last
3. **Graceful degradation** — slow modules (IIT Φ) don't block the main loop
4. **Auditability** — every cycle produces a `CycleResult` written to the Blackboard

---

## 9-Phase Architecture

Each tick of the `CognitiveCycle` runs in 9 sequential phases:

| Phase | Name | Primary Modules | Notes |
|-------|------|-----------------|-------|
| 1 | **Sensory Integration** | `bci`, `sensory_integration` | Ingest raw inputs |
| 2 | **Perception** | `bio_inspired` | Feature extraction, preprocessing |
| 3 | **Attention** | `consciousness` (AST, GWT) | Gate what enters working memory |
| 4 | **Consciousness** | `consciousness` (IIT Φ, GWT broadcast) | Rate-limited; reads async Φ from Blackboard |
| 5 | **Knowledge Update** | `knowledge_graph`, `knowledge_management` | Write new percepts to bi-temporal KG |
| 6 | **Reasoning** | `reasoning`, `graph_intelligence`, `pln_accelerator` | Generate hypotheses |
| 7 | **Decision** | `cognitive_synergy` | Arbitrate between competing hypotheses |
| 8 | **Action** | `agi_communication`, Blackboard publish | Execute selected action |
| 9 | **Safety Gate** | `safety` (EthicalVerificationEngine) | **Synchronous veto** — blocks action if unsafe |

Phase 9 is the only phase that can abort the cycle. If `safety.verify()` returns `False`, the action from Phase 8 is cancelled and the `CycleResult` records the veto.

---

## Data Structures

### `CycleResult`

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class CycleResult:
    cycle_id: int
    tick_ms: float                      # target tick duration

    # Phase outputs
    sensory_snapshot: dict[str, Any]    # Phase 1
    perception_result: dict[str, Any]   # Phase 2
    attention_state: dict[str, Any]     # Phase 3
    phi: float                          # Phase 4 — IIT Φ (may be stale)
    phi_age_ticks: int                  # how many ticks since last Φ computation
    active_hypotheses: list[dict]       # Phase 6
    selected_action: dict[str, Any]     # Phase 7
    action_executed: bool               # Phase 8 — False if safety veto
    safety_verdict: dict[str, Any]      # Phase 9

    # Module accounting
    modules_run: list[str]
    modules_skipped: list[str]
    blackboard_writes: int

    # Performance diagnostics
    wall_time_ms: float
    phase_times_ms: dict[str, float] = field(default_factory=dict)
```

`CycleResult` is written to the Blackboard at the end of each tick under key `"cognitive_cycle/last_result"`. Modules can inspect it on the next tick.

---

## The IIT Φ Problem

IIT Φ is computationally expensive. With a 2-node TPM it takes ~0.059ms (see [Benchmark Results](Benchmark-Results)), but IIT scales **exponentially** with the number of nodes. An 8-node network may take 50–500ms — far exceeding a 25ms tick budget.

### Option A: Rate Limiting (Synchronous)

```python
class CognitiveCycle:
    def __init__(self, phi_every_n_ticks: int = 10):
        self._phi_interval = phi_every_n_ticks
        self._ticks_since_phi = 0
        self._last_phi = 0.0

    def _run_phase4(self) -> float:
        self._ticks_since_phi += 1
        if self._ticks_since_phi >= self._phi_interval:
            self._last_phi = self.iit.compute_phi(...)
            self._ticks_since_phi = 0
        return self._last_phi
```

**Pro**: Simple, deterministic.  
**Con**: Φ computation blocks the tick when it runs.

### Option B: Async Worker (Recommended)

```python
class CognitiveCycle:
    def start(self):
        self._phi_thread = threading.Thread(target=self._phi_worker, daemon=True)
        self._phi_thread.start()

    def _phi_worker(self):
        """Runs independently; adapts interval to actual computation time."""
        while self._running:
            start = time.monotonic()
            phi = self.iit.compute_phi(
                self.blackboard.query("activation_patterns")
            )
            self.blackboard.write("consciousness/phi", phi, source="iit_worker")
            elapsed = time.monotonic() - start
            # Sleep for same duration as computation (50% duty cycle)
            time.sleep(elapsed)

    def _run_phase4(self) -> tuple[float, int]:
        """Reads last known Φ from Blackboard — never blocks."""
        entry = self.blackboard.query("consciousness/phi")
        phi = entry.value if entry else 0.0
        age = self._ticks_since(entry.timestamp) if entry else -1
        return phi, age
```

**Pro**: Main loop runs at consistent 40Hz; Φ runs as fast as hardware allows.  
**Con**: Φ value is always slightly stale; adds thread coordination complexity.

**Current recommendation**: Option B. The Blackboard is thread-safe (verified in the integration layer), so this is well-supported by existing infrastructure.

---

## Tick Rate

**Target: 40Hz (25ms budget)**

This is inspired by the gamma oscillation (~40Hz) hypothesis in neuroscience — the brain's binding frequency. It is not a hard requirement; it is a useful design target.

Proposed adaptive tick:
- If wall time < 20ms: sleep the remainder
- If wall time 20–25ms: run at natural speed, no sleep
- If wall time > 25ms: emit `CycleOverrunWarning` to EventBus, skip lowest-priority modules next tick

Modules skipped on overrun (in order): `pln_accelerator`, `graph_intelligence`, `knowledge_update`.  
Modules **never** skipped: `safety` (Phase 9), `attention` (Phase 3).

---

## Blackboard Integration

The Cognitive Cycle is the primary **writer** to the Blackboard during normal operation. Each phase writes its output:

```
cognitive_cycle/sensory          ← Phase 1
cognitive_cycle/perception       ← Phase 2
cognitive_cycle/attention        ← Phase 3
consciousness/phi                ← Phase 4 (async worker)
knowledge_graph/updates          ← Phase 5
reasoning/hypotheses             ← Phase 6
decision/selected_action         ← Phase 7
cognitive_cycle/action_result    ← Phase 8
safety/last_verdict              ← Phase 9
cognitive_cycle/last_result      ← Full CycleResult (end of tick)
```

Other modules can subscribe to these keys via the EventBus to react to cycle outputs without being in the critical path.

---

## Module Adapters

The four existing adapters in `src/asi_build/integration/adapters/` already implement the `IModuleAdapter` protocol:

| Adapter | Wraps | Used in phase |
|---------|-------|---------------|
| `ConsciousnessAdapter` | `ConsciousnessOrchestrator` | 3, 4 |
| `SafetyAdapter` | `EthicalVerificationEngine` | 9 |
| `KnowledgeAdapter` | `KnowledgeGraphEngine` | 5 |
| `ReasoningAdapter` | `ReasoningEngine` | 6 |

The `CognitiveCycle` will use these adapters, not the underlying modules directly. This preserves the integration layer abstraction.

---

## Testing Plan

Three levels of tests for the `CognitiveCycle`:

### Unit tests (fast)
```python
def test_cycle_result_fields():
    """CycleResult has all required fields."""

def test_safety_veto_blocks_action():
    """Phase 9 veto sets action_executed=False."""

def test_phi_fallback_on_timeout():
    """Stale Φ does not crash the cycle."""
```

### Integration tests (with real adapters)
```python
def test_full_9phase_cycle():
    """All 9 phases run without exception; CycleResult written to Blackboard."""

def test_cycle_result_readable_next_tick():
    """Second tick can read last_result from first tick."""
```

### Performance tests
```python
def test_tick_rate_40hz():
    """100 ticks complete in <2600ms (10% margin)."""

def test_phi_async_does_not_block_tick():
    """Φ worker runs; tick wall_time_ms stays under 25ms."""
```

---

## Open Questions

1. **Φ async vs. rate-limit** — see [Discussion #40](https://github.com/web3guru888/asi-build/discussions/40)
2. **Module discovery** — should `CognitiveCycle` auto-discover adapters via entry points, or be constructed with an explicit list?
3. **Multi-agent extension** — if multiple `CognitiveCycle` instances run in parallel (e.g., Rings Network peers), how do they synchronize KG writes?
4. **Introspection API** — should there be a `CognitiveCycle.inspect()` that returns the current `CycleResult` without waiting for the next tick?

---

## Related Pages

- [Cognitive Blackboard](Cognitive-Blackboard) — the shared memory the cycle writes to
- [Architecture](Architecture) — overall layered design
- [Consciousness Module](Consciousness-Module) — IIT Φ, GWT, AST implementations
- [Safety Module](Safety-Module) — EthicalVerificationEngine (Phase 9)
- [Benchmark Results](Benchmark-Results) — IIT Φ timing data
- [Rings Network](Rings-Network) — distributed multi-agent extension
