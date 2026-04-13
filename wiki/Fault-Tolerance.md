# Fault Tolerance in the CognitiveCycle

The `CognitiveCycle` runs 29 modules across 5 dependency tiers every tick. In a production system, failures are inevitable — modules timeout, resources spike, network calls blip. This page documents the three-layer fault tolerance architecture that keeps the cycle running despite partial failures.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     CognitiveCycle.tick()                       │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │ Retry Budget │ → │Circuit Breaker│ → │ Graceful Degrade   │  │
│  │ (innermost)  │   │  (middle)    │   │ (outermost)        │  │
│  └──────────────┘   └──────────────┘   └────────────────────┘  │
│                                                                 │
│  Transient failures → Persistent failures → Cascade failures    │
└─────────────────────────────────────────────────────────────────┘
```

**Layer 1 (Retry Budget)** absorbs transient failures within a tick.  
**Layer 2 (Circuit Breaker)** isolates persistently failing modules across ticks.  
**Layer 3 (Graceful Degradation)** keeps the cycle useful even when modules are offline.

---

## Layer 1: Retry Budget

The innermost layer. Provides bounded retries with exponential backoff within a hard wall-clock budget.

### Design

```python
from dataclasses import dataclass
from typing import Optional
import asyncio
import time

@dataclass
class RetryBudget:
    max_attempts: int = 3           # including first attempt
    base_delay_ms: float = 10.0     # first retry delay
    backoff_factor: float = 2.0     # exponential multiplier
    max_delay_ms: float = 100.0     # cap per-retry wait
    budget_ms: float = 250.0        # total wall-clock cap for all attempts

class RetryBudgetExhausted(Exception):
    """Raised when all retry attempts are spent or budget_ms exceeded."""
    pass

async def run_with_retry(
    module: "CognitiveModule",
    ctx: "CycleContext",
    budget: RetryBudget,
) -> "ModuleResult":
    start = time.monotonic()
    delay_ms = budget.base_delay_ms
    last_exc: Optional[Exception] = None

    for attempt in range(budget.max_attempts):
        elapsed_ms = (time.monotonic() - start) * 1000
        remaining_ms = budget.budget_ms - elapsed_ms
        if remaining_ms <= 0:
            raise RetryBudgetExhausted(
                f"{module.name}: budget {budget.budget_ms}ms exceeded after {attempt} attempts"
            )
        try:
            return await asyncio.wait_for(
                module.run(ctx),
                timeout=remaining_ms / 1000,
            )
        except (asyncio.TimeoutError, TransientModuleError) as exc:
            last_exc = exc
            if attempt < budget.max_attempts - 1:
                wait = min(delay_ms, budget.max_delay_ms) / 1000
                await asyncio.sleep(wait)
                delay_ms *= budget.backoff_factor

    raise RetryBudgetExhausted(
        f"{module.name}: {budget.max_attempts} attempts exhausted"
    ) from last_exc
```

### Per-Tier Configuration

| Tier | Examples | max_attempts | budget_ms | Notes |
|------|----------|:-----------:|:--------:|-------|
| 0 — Safety | safety, ethical_verification | **1** | 50 | No retry — failures escalate immediately |
| 1 — Knowledge | knowledge_graph, reasoning | 3 | 200 | Standard backoff |
| 2 — Perception | BCI, holographic, neuromorphic | 2 | 150 | Sensor latency tolerance |
| 3 — Planning | agi_communication, economics | 2 | 100 | Agent coordination timeout |
| 4 — Execution | deployment, servers | 2 | 100 | Network I/O bounded |

**Safety modules do not retry.** A single safety gate failure must escalate immediately to the circuit breaker, not be swallowed and retried.

### What Counts as Retryable?

```python
class TransientModuleError(Exception):
    """Base for errors the retry budget will absorb."""
    pass

class PermanentModuleError(Exception):
    """Base for errors that bypass retry and go straight to circuit breaker."""
    pass
```

- `asyncio.TimeoutError` → retryable
- `TransientModuleError` (subclasses) → retryable
- `PermanentModuleError` → bypass to circuit breaker
- `RetryBudgetExhausted` → escalates to circuit breaker

---

## Layer 2: Circuit Breaker

The middle layer. Operates on *ticks*, not individual calls. Counts `RetryBudgetExhausted` events across ticks; after a threshold, opens the circuit and skips the module entirely.

### State Machine

```
        ┌──────────────────┐
  ─────▶│     CLOSED       │◀─────────────────┐
  start │ (normal traffic) │                  │
        └────────┬─────────┘            success_threshold
                 │                      probe successes
          failure_threshold                    │
         (RetryBudgetExhausted)                │
                 │                     ┌───────┴──────────┐
                 ▼                     │    HALF_OPEN     │
        ┌──────────────────┐           │  (probe request) │
        │      OPEN        │◀──────────┤                  │
        │ (skip module)    │  probe    │  (1 attempt/tick)│
        └────────┬─────────┘  fails   └───────┬──────────┘
                 │                             ▲
          recovery_timeout_s                   │
          (time.monotonic)                     │
                 └─────────────────────────────┘
```

### Implementation

```python
from enum import Enum
from dataclasses import dataclass, field
import time

class CircuitState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreaker:
    module_name: str
    failure_threshold: int = 5          # budget exhaustions before OPEN
    recovery_timeout_s: float = 30.0    # wait before HALF_OPEN
    success_threshold: int = 2          # consecutive successes to re-CLOSE

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: float = 0.0
    last_failure: Optional[Exception] = None

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._close()
        else:
            self.failure_count = 0  # reset on healthy tick

    def record_failure(self, exc: Exception) -> None:
        self.last_failure = exc
        if self.state == CircuitState.HALF_OPEN:
            self._open()  # probe failed → re-open immediately
        else:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._open()

    def should_allow(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if (time.monotonic() - self.opened_at) >= self.recovery_timeout_s:
                self._half_open()
                return True  # allow single probe
            return False
        # HALF_OPEN: allow one probe at a time
        return True

    def _open(self) -> None:
        self.state = CircuitState.OPEN
        self.opened_at = time.monotonic()
        self.success_count = 0

    def _close(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0

    def _half_open(self) -> None:
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
```

### Per-Tier Thresholds

Safety-critical modules are more conservative — fewer failures allowed before the circuit opens, longer recovery windows:

| Tier | failure_threshold | recovery_timeout_s | success_threshold |
|------|:-----------------:|:------------------:|:-----------------:|
| 0 — Safety | 2 | 60 | 3 |
| 1 — Knowledge | 5 | 30 | 2 |
| 2 — Perception | 7 | 20 | 2 |
| 3 — Planning | 10 | 15 | 1 |
| 4 — Execution | 10 | 10 | 1 |

### Blackboard Events

Every state transition publishes to the Blackboard:

| Entry Key | Value Schema | Tier |
|-----------|-------------|------|
| `circuit.<name>.state` | `{state, failure_count, opened_at}` | Informational |
| `circuit.<name>.opened` | `{module, last_error, tier, tick_id}` | Warning |
| `circuit.<name>.probing` | `{module, downtime_s, attempt}` | Informational |
| `circuit.<name>.closed` | `{module, downtime_s, probe_successes}` | Informational |
| `circuit.EMERGENCY` | `{open_safety_circuits, tick_id}` | Critical |

---

## Layer 3: Graceful Degradation

The outermost layer. Even with circuit breakers, some modules are load-bearing — their output feeds downstream tiers. Graceful degradation keeps those downstream modules functional.

### Strategy A: Last-Known-Good Cache

```python
@dataclass
class ModuleLastGood:
    entry: BlackboardEntry
    written_at: float   # monotonic timestamp
    ttl_s: float = 5.0  # max acceptable staleness

    @property
    def is_valid(self) -> bool:
        return (time.monotonic() - self.written_at) < self.ttl_s

class CognitiveCycle:
    _last_good: dict[str, ModuleLastGood] = {}

    async def _run_tier(self, tier_modules, ctx):
        for module in tier_modules:
            breaker = self._breakers[module.name]
            if not breaker.should_allow():
                # Reuse last-good output if still fresh
                for key in module.blackboard_output_keys:
                    cached = self._last_good.get(key)
                    if cached and cached.is_valid:
                        await self._blackboard.publish(cached.entry)
                continue
            # ... normal execution; update _last_good on success
```

### Strategy B: Partial Tier Execution

Run the remaining healthy modules in a tier even when some circuits are open. Downstream modules receive `None` for missing upstream inputs and must handle it:

```python
# Each module should declare which upstream keys are optional
class HybridReasoningEngine(CognitiveModule):
    optional_inputs = {"bio_state", "quantum_result"}
    required_inputs = {"knowledge_graph.current"}
```

### Strategy C: Emergency Minimal Mode

Triggered when the Tier 0 (safety) circuit opens:

```python
class EmergencyMode:
    MINIMAL_MODULES = {"safety", "ethical_verification"}

    async def run_emergency_tick(self, ctx: CycleContext) -> CycleResult:
        """Skip all non-safety modules. Run safety with last-known-good inputs."""
        for name in self._safety_modules:
            await self._run_module_with_retry(name, ctx, budget=SAFETY_EMERGENCY_BUDGET)

        # If safety still fails, emit EMERGENCY_STOP
        if not self._safety_confirmed:
            await self._blackboard.publish(BlackboardEntry(
                key="safety.EMERGENCY_STOP",
                value={"reason": "safety_circuit_open", "tick_id": ctx.tick_id},
                source="CognitiveCycle",
            ))
```

---

## Integration: CognitiveCycle._run_tier()

The three layers compose naturally inside `_run_tier()`:

```python
async def _run_tier(
    self,
    tier_modules: list[CognitiveModule],
    ctx: CycleContext,
) -> list[ModuleResult]:
    results: list[ModuleResult] = []
    tasks: list[asyncio.Task] = []
    active_modules: list[CognitiveModule] = []

    for module in tier_modules:
        breaker = self._breakers[module.name]
        if not breaker.should_allow():
            await self._apply_last_good(module)
            results.append(ModuleResult(module=module.name, skipped=True, reason="circuit_open"))
            continue
        active_modules.append(module)
        budget = self._tier_budgets[module.tier]
        tasks.append(asyncio.create_task(
            run_with_retry(module, ctx, budget)
        ))

    raw = await asyncio.gather(*tasks, return_exceptions=True)

    for module, outcome in zip(active_modules, raw):
        breaker = self._breakers[module.name]
        if isinstance(outcome, Exception):
            breaker.record_failure(outcome)
            results.append(ModuleResult(module=module.name, error=outcome))
        else:
            breaker.record_success()
            self._update_last_good(module, outcome)
            results.append(outcome)

    return results
```

---

## Observability: CycleFaultSummary

Every tick, a fault summary is written to the Blackboard and captured by the `CycleProfiler`:

```python
@dataclass
class CycleFaultSummary:
    tick_id: int
    open_circuits: list[str]          # module names with OPEN state
    half_open_circuits: list[str]     # modules being probed
    retry_counts: dict[str, int]      # module -> retries consumed this tick
    degraded_keys: list[str]          # Blackboard keys served from last-good cache
    emergency_mode: bool
    wall_ms: float                    # total tick duration
```

---

## Testing

### Unit Tests

```python
async def test_retry_absorbs_transient_failure():
    budget = RetryBudget(max_attempts=3, base_delay_ms=1, budget_ms=500)
    attempt = 0
    async def flaky_run(ctx):
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise TransientModuleError("spike")
        return ModuleResult(module="test", success=True)
    result = await run_with_retry(FakeModule(flaky_run), ctx, budget)
    assert result.success and attempt == 3

async def test_circuit_opens_after_threshold():
    cb = CircuitBreaker(module_name="test", failure_threshold=3)
    for _ in range(3):
        cb.record_failure(RetryBudgetExhausted("test"))
    assert cb.state == CircuitState.OPEN
    assert not cb.should_allow()

async def test_last_good_served_when_circuit_open():
    cycle = CognitiveCycle(modules=[...])
    # Pre-populate last-good cache
    cycle._last_good["reasoning.result"] = ModuleLastGood(
        entry=BlackboardEntry(key="reasoning.result", value={"confidence": 0.8}),
        written_at=time.monotonic(),
        ttl_s=10.0,
    )
    # Trip the circuit
    for _ in range(5):
        cycle._breakers["reasoning"].record_failure(RetryBudgetExhausted(""))
    # Run tier — should serve last-good
    result = await cycle._run_tier([reasoning_module], ctx)
    assert result[0].skipped
    blackboard_entry = await cycle._blackboard.get("reasoning.result")
    assert blackboard_entry.value["confidence"] == 0.8
```

### Integration Tests

| Test | Setup | Expected |
|------|-------|---------|
| Tier 1 circuit open, Tier 2 gets last-good | Trip reasoning circuit | Tier 2 runs with stale reasoning.result |
| Safety circuit opens → emergency mode | Trip safety breaker | Tick skips Tiers 1-4, publishes EMERGENCY_STOP |
| Recovery: HALF_OPEN → CLOSED after probes | Trip + wait recovery_timeout | 2 successful probes → CLOSED |
| Budget exhaustion propagates to breaker | Consistently timeout module | failure_count increments each tick |

---

## Open Design Questions

1. **Staleness propagation** — when module A uses a last-good value from T-3s, should module B's output that depends on A be tagged as `derived_from_stale`? This would allow downstream consumers to discount confidence appropriately.

2. **Safety module recovery** — should Tier 0 `recovery_timeout_s` be automatic (current design) or require a human operator to manually clear the circuit? A safety logic bug is different from a transient timeout.

3. **Circuit breaker persistence** — the current design resets all circuit breakers on process restart. Should circuit state be persisted to the Blackboard (or a file) so a restarted process doesn't immediately retry all previously-failing modules?

4. **Shared vs. per-instance breakers** — if the same module class is instantiated 3 times (e.g., 3 BCI sensors), should they share one circuit breaker or have independent ones?

---

## Related Issues & Discussions

| Link | Topic |
|------|-------|
| [#134](https://github.com/web3guru888/asi-build/issues/134) | Fault tolerance strategies: fail-fast vs. graceful degradation |
| [#137](https://github.com/web3guru888/asi-build/issues/137) | Circuit breaker implementation |
| [#139](https://github.com/web3guru888/asi-build/issues/139) | Retry budget manager |
| [#133](https://github.com/web3guru888/asi-build/issues/133) | Parallel tier execution |
| [#144](https://github.com/web3guru888/asi-build/issues/144) | CycleFaultSummary + SSE health endpoint |
| [#126](https://github.com/web3guru888/asi-build/issues/126) | CycleProfiler (timing + fault summary) |
| [Discussion #142](https://github.com/web3guru888/asi-build/discussions/142) | Show & Tell: fault tolerance design walkthrough |
| [Discussion #143](https://github.com/web3guru888/asi-build/discussions/143) | Ideas: health dashboard for operators |
| [Discussion #138](https://github.com/web3guru888/asi-build/discussions/138) | Per-tier timeout strategies |
| [Discussion #145](https://github.com/web3guru888/asi-build/discussions/145) | Q&A: debugging slow CognitiveCycle ticks |
