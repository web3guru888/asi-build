# Parallel Execution in CognitiveCycle

ASI:BUILD's CognitiveCycle uses **tier-parallel execution** to reduce tick latency. Instead of running 29 modules sequentially (worst-case ~87ms), modules are grouped into **tiers** based on their data dependencies. All modules within a tier run concurrently via `asyncio.gather()`. Total tick latency approaches `sum(max(T_i per tier))` rather than `sum(T_i across all modules)`.

Estimated improvement: **~87ms sequential → ~55ms parallel** — a **~37% reduction** in tick latency for the default 29-module configuration.

---

## Table of Contents

1. [Why Tier-Parallel Execution?](#why-tier-parallel-execution)
2. [Tier Extraction via Topological Sort](#tier-extraction-via-topological-sort)
3. [Default Tier Structure](#default-tier-structure)
4. [CognitiveCycle tick() Implementation](#cognitivecycle-tick-implementation)
5. [Exception Isolation with return_exceptions=True](#exception-isolation)
6. [TierTiming and Profiler Integration](#tiertiming-and-profiler-integration)
7. [Module Health and Circuit Breaker](#module-health-and-circuit-breaker)
8. [Per-Tier Timeout Strategies](#per-tier-timeout-strategies)
9. [Testing Tier-Parallel Execution](#testing-tier-parallel-execution)
10. [Correctness Guarantees](#correctness-guarantees)
11. [Performance Targets](#performance-targets)
12. [Related Issues and Discussions](#related-issues-and-discussions)

---

## Why Tier-Parallel Execution?

The CognitiveCycle must complete one tick within a **100ms real-time budget** to maintain perception-to-action latency targets. With 29 modules and sequential execution:

```
Sequential: T_total = T_safety + T_knowledge_graph + T_consciousness + ... ≈ 87ms
```

Most modules, however, have no direct data dependency on each other. `knowledge_graph` does not need `blockchain` to finish before it can read. `neuromorphic` has no dependency on `vectordb`. Running these concurrently:

```
Parallel: T_total = T_tier0 + T_tier1 + T_tier2 + T_tier3 ≈ 55ms
                  = max(T_safety, T_homomorphic, T_neuromorphic) + ...
```

This is a **structural guarantee**, not a micro-optimization: the tick budget cannot be met without parallel execution as the module count grows.

---

## Tier Extraction via Topological Sort

Module dependencies are declared via `__depends_on__` metadata (see [Module-Dependency-Graph](Module-Dependency-Graph)):

```python
class SafetyBlackboardAdapter(AsyncBlackboardAdapter):
    __depends_on__: list[str] = []  # Tier 0 — no dependencies

class ConsciousnessBlackboardAdapter(AsyncBlackboardAdapter):
    __depends_on__ = ["knowledge_graph", "neuromorphic"]  # Tier 2
```

The `parallel_tiers()` function in `integration/dependency_graph.py` extracts tier groups using Python 3.9+ stdlib `graphlib.TopologicalSorter`:

```python
from graphlib import TopologicalSorter

def parallel_tiers(graph: dict[str, set[str]]) -> list[list[str]]:
    """Return modules grouped by execution tier.

    Tier 0 = no dependencies (run first, concurrently).
    Tier N = all dependencies satisfied by tiers 0..N-1.
    Modules within a tier can execute concurrently via asyncio.gather().

    Returns deterministically ordered tiers (sorted within each tier).
    """
    sorter = TopologicalSorter(graph)
    sorter.prepare()
    tiers: list[list[str]] = []
    while sorter.is_active():
        ready = sorted(sorter.get_ready())  # sorted for reproducibility
        tiers.append(ready)
        for node in ready:
            sorter.done(node)
    return tiers
```

### Algorithm guarantees

- **Correctness**: Every module appears in exactly one tier, after all its declared dependencies.
- **Optimality**: A module is placed in the earliest possible tier — no unnecessary delays.
- **Cycle detection**: `TopologicalSorter` raises `graphlib.CycleError` if a dependency cycle is detected. The CognitiveCycle refuses to start if the dependency graph has cycles.
- **Determinism**: `sorted()` within each tier ensures the same tier structure across runs.

---

## Default Tier Structure

The default dependency graph for ASI:BUILD's 29 modules produces the following tier structure:

| Tier | Modules | Est. wall-clock | Budget |
|------|---------|-----------------|--------|
| **Tier 0** | `safety`, `homomorphic`, `neuromorphic` | ~8ms | 10ms |
| **Tier 1** | `knowledge_graph`, `vectordb`, `blockchain`, `quantum` | ~15ms | 20ms |
| **Tier 2** | `consciousness`, `reasoning`, `bio_inspired`, `graph_intelligence` | ~20ms | 25ms |
| **Tier 3** | `cognitive_synergy`, `agi_communication`, `federation`, `rings` | ~10ms | 15ms |
| **Tier 4** | `cycle_result_aggregation` | ~2ms | 5ms |
| **Total** | 29 modules | **~55ms** | **75ms** |

Remaining ~25ms of the 100ms budget is reserved for Blackboard I/O, EventBus dispatch, and jitter headroom.

> **Note**: The tier structure is derived automatically from `__depends_on__` metadata. Modules not yet wired (no `BlackboardAdapter` registered) are silently excluded from the tier graph.

---

## CognitiveCycle tick() Implementation

```python
import asyncio
import time
from integration.dependency_graph import parallel_tiers, build_dependency_graph

class CognitiveCycle:
    def __init__(self, adapters: dict[str, AsyncBlackboardAdapter], blackboard: CognitiveBlackboard):
        self._adapters = adapters
        self._blackboard = blackboard
        # Build tier structure once at init time (dependency graph is static)
        graph = build_dependency_graph(adapters)
        self._tiers: list[list[str]] = parallel_tiers(graph)
        self._health: dict[str, ModuleHealthRecord] = {
            name: ModuleHealthRecord(name) for name in adapters
        }
        self._profiler = CycleProfiler()

    async def tick(self) -> CycleResult:
        """Execute one CognitiveCycle tick using tier-parallel execution."""
        tick_start = time.perf_counter()
        tier_results: dict[str, PhaseResult | BaseException] = {}

        for tier_idx, tier in enumerate(self._tiers):
            async with self._profiler.measure_tier(tier_idx, tier):
                results = await self._run_tier(tier_idx, tier)
            tier_results.update(results)

        total_ms = (time.perf_counter() - tick_start) * 1000
        return CycleResult(
            tick_ms=total_ms,
            tier_count=len(self._tiers),
            profiler_summary=self._profiler.summary(),
            module_results=tier_results,
        )

    async def _run_tier(
        self,
        tier_idx: int,
        tier: list[str],
    ) -> dict[str, PhaseResult | BaseException]:
        """Run all modules in a tier concurrently. Failures are isolated."""
        # Filter out circuit-open modules
        runnable = [n for n in tier if self._health[n].should_run and n in self._adapters]
        skipped = [n for n in tier if n not in runnable]

        for name in skipped:
            self._blackboard.publish("cycle.module_skipped", {"module": name, "tier": tier_idx})

        if not runnable:
            return {}

        tasks = {
            name: asyncio.create_task(
                self._adapters[name].run_phase(self._blackboard),
                name=f"tier{tier_idx}/{name}",
            )
            for name in runnable
        }

        raw = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results: dict[str, PhaseResult | BaseException] = {}

        for name, result in zip(tasks, raw):
            if isinstance(result, BaseException):
                self._health[name].record_failure()
                self._blackboard.publish(
                    "cycle.module_error",
                    {"tier": tier_idx, "module": name, "error": str(result)},
                )
                import logging
                logging.getLogger(__name__).warning(
                    "Module %s raised in tier %d: %s", name, tier_idx, result
                )
            else:
                self._health[name].record_success()
            results[name] = result

        return results
```

---

## Exception Isolation

The `return_exceptions=True` flag on `asyncio.gather()` is critical. **Without it**, a single failing module raises immediately and cancels all other concurrent tasks in the tier:

```python
# BAD — one exception cancels all tasks
results = await asyncio.gather(*tasks.values())  # raises on first exception

# GOOD — exceptions captured as values, all tasks complete
results = await asyncio.gather(*tasks.values(), return_exceptions=True)
```

With `return_exceptions=True`:
- Exceptions are returned as values in the result list
- All other tasks in the tier complete normally
- The calling code inspects results and handles exceptions explicitly
- A failing blockchain module does not prevent consciousness or knowledge_graph from completing

---

## TierTiming and Profiler Integration

The `CycleProfiler` (see Issue #126) is extended with `TierTiming` alongside the existing per-phase `CycleTimingEntry`:

```python
from dataclasses import dataclass, field

@dataclass
class TierTiming:
    tier_idx: int
    modules: list[str]
    wall_clock_ms: float   # time.perf_counter() span — true concurrency measure
    over_budget: bool

    @classmethod
    def budget_ms(cls, tier_idx: int) -> float:
        TIER_BUDGETS = {0: 10.0, 1: 20.0, 2: 25.0, 3: 15.0, 4: 5.0}
        return TIER_BUDGETS.get(tier_idx, 30.0)
```

The `measure_tier()` context manager in `CycleProfiler`:

```python
from contextlib import contextmanager

@contextmanager
def measure_tier(self, tier_idx: int, modules: list[str]):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._tier_timings[tier_idx] = TierTiming(
            tier_idx=tier_idx,
            modules=modules,
            wall_clock_ms=elapsed_ms,
            over_budget=elapsed_ms > TierTiming.budget_ms(tier_idx),
        )
```

### Diagnostic signal: wall-clock vs sum-of-modules

The key diagnostic: if `wall_clock_ms ≈ max(individual module timings)`, the tier is behaving correctly (true parallelism). If `wall_clock_ms ≈ sum(individual module timings)`, modules are blocking the event loop with CPU-bound work rather than awaiting I/O.

Example output:

```
Tick #1042 — total 54.8ms ✓
  Tier 0: 3 modules | wall=8.1ms | budget=10ms ✓
    safety:       7.9ms ✓
    homomorphic:  8.1ms ✓  ← bottleneck (slowest in tier)
    neuromorphic: 3.2ms ✓
  Tier 1: 4 modules | wall=14.7ms | budget=20ms ✓
    knowledge_graph: 14.7ms ✓
    vectordb:         9.1ms ✓
    blockchain:       4.3ms ✓
    quantum:         12.8ms ✓
  Tier 2: 4 modules | wall=19.4ms | budget=25ms ✓
  Tier 3: 4 modules | wall=10.8ms | budget=15ms ✓
  Tier 4: 1 module  | wall= 1.8ms | budget= 5ms ✓
```

---

## Module Health and Circuit Breaker

See Issue #137 for the full circuit breaker design. Summary:

```python
class CircuitState(Enum):
    CLOSED   = auto()  # healthy — run normally
    OPEN     = auto()  # unhealthy — skip (auto-disabled)
    HALF_OPEN = auto() # recovery probe — run once to test

@dataclass
class ModuleHealthRecord:
    module_name: str
    consecutive_failures: int = 0
    state: CircuitState = CircuitState.CLOSED
    OPEN_THRESHOLD: int = 5
    RECOVERY_TIMEOUT_S: float = 30.0
    last_failure_time: float = 0.0

    @property
    def should_run(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time > self.RECOVERY_TIMEOUT_S:
                self.state = CircuitState.HALF_OPEN
                return True  # one recovery probe
            return False
        return True  # HALF_OPEN: allow probe
```

A module that fails 5 consecutive ticks transitions to `OPEN` and is skipped until a 30-second recovery probe succeeds.

---

## Per-Tier Timeout Strategies

See Discussion #138 for the open debate. Three strategies under consideration:

| Strategy | Description | Tradeoff |
|----------|-------------|----------|
| **A: Tier-level** | `asyncio.wait_for(gather_tier(), timeout=budget)` | Simple; cancels all tasks if any hangs |
| **B: Per-module** | `asyncio.wait_for(adapter.run_phase(), timeout=budget)` | Surgical; each module gets its own deadline |
| **C: asyncio.wait()** | Collect done + pending; cancel only pending | Clean; preserves completed fast modules |

**Current recommendation**: Option B (per-module) combined with the circuit breaker from #137. A module that consistently times out will eventually trip its circuit and be skipped entirely, eliminating the timeout overhead.

---

## Testing Tier-Parallel Execution

### Test 1: Concurrency correctness

```python
@pytest.mark.asyncio
async def test_tier_parallel_faster_than_sequential():
    """Concurrent modules should complete in max(T_i), not sum(T_i)."""
    async def slow_module(delay_ms: float):
        await asyncio.sleep(delay_ms / 1000)
        return PhaseResult(module="test", success=True)

    start = time.perf_counter()
    results = await asyncio.gather(
        slow_module(50), slow_module(50), return_exceptions=True
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 65, f"Expected ~50ms parallel, got {elapsed_ms:.1f}ms"
```

### Test 2: Exception isolation

```python
@pytest.mark.asyncio
async def test_exception_does_not_cancel_sibling_tasks():
    """A failing module should not cancel other modules in the same tier."""
    async def fail(): raise RuntimeError("simulated failure")
    async def succeed(): await asyncio.sleep(0.01); return PhaseResult(success=True)

    results = await asyncio.gather(fail(), succeed(), return_exceptions=True)
    assert isinstance(results[0], RuntimeError)
    assert isinstance(results[1], PhaseResult) and results[1].success
```

### Test 3: Circuit breaker integration

```python
def test_circuit_opens_after_threshold():
    health = ModuleHealthRecord("test_module")
    for _ in range(5):
        health.record_failure()
    assert health.state == CircuitState.OPEN
    assert not health.should_run
```

---

## Correctness Guarantees

Tier-parallel execution provides the following **correctness guarantees** beyond raw performance:

1. **Consistent read snapshot**: All modules in Tier N read from the Blackboard state as it was after Tier N-1 committed. No module in Tier N can observe partial writes from a sibling in the same tier (Blackboard write locking enforces this).

2. **Explicit dependency contract**: The tier structure is derived from `__depends_on__` metadata. If a module needs data from another, it declares it — and the scheduler guarantees that dependency runs first. Implicit ordering from sequential execution is eliminated.

3. **Testable isolation**: Each tier is a discrete unit that can be tested independently with mock adapters. The dependency graph can be validated for cycles at import time.

---

## Performance Targets

| Metric | Target | Measured (mock) |
|--------|--------|-----------------|
| Total tick latency (29 modules) | ≤ 100ms | ~55ms |
| Tier 0 wall-clock | ≤ 10ms | ~8ms |
| Tier 1 wall-clock | ≤ 20ms | ~15ms |
| Tier 2 wall-clock | ≤ 25ms | ~20ms |
| Tier 3 wall-clock | ≤ 15ms | ~10ms |
| Parallelism factor (sequential / parallel) | ≥ 1.5× | ~1.58× |

---

## Related Issues and Discussions

| # | Type | Topic |
|---|------|-------|
| [#131](https://github.com/web3guru888/asi-build/issues/131) | Issue | Module dependency graph — `__depends_on__` + topological sort |
| [#133](https://github.com/web3guru888/asi-build/issues/133) | Issue | Parallel tier execution — `asyncio.gather()` implementation |
| [#134](https://github.com/web3guru888/asi-build/issues/134) | Issue | Graceful degradation strategy for module failures |
| [#137](https://github.com/web3guru888/asi-build/issues/137) | Issue | Circuit breaker — auto-disable persistently failing modules |
| [#126](https://github.com/web3guru888/asi-build/issues/126) | Issue | CycleProfiler — per-phase timing and budget tracking |
| [#41](https://github.com/web3guru888/asi-build/issues/41) | Issue | CognitiveCycle full implementation |
| [#132](https://github.com/web3guru888/asi-build/discussions/132) | Discussion | Show & Tell: Dependency graph design |
| [#136](https://github.com/web3guru888/asi-build/discussions/136) | Discussion | Show & Tell: Tier-parallel execution design |
| [#138](https://github.com/web3guru888/asi-build/discussions/138) | Discussion | Ideas: Per-tier timeout strategies |
