# Async Architecture

> **Status**: Design Phase 🔮  
> **Issue**: [#101 — AsyncBlackboardAdapter base class](https://github.com/web3guru888/asi-build/issues/101)  
> **Discussion**: [#113 — Designing the AsyncBlackboardAdapter](https://github.com/web3guru888/asi-build/discussions/113)  
> **Related**: [Integration Layer](Integration-Layer), [Cognitive Blackboard](Cognitive-Blackboard), [CognitiveCycle](CognitiveCycle)

---

## Why async matters

ASI:BUILD's current Blackboard adapters are **synchronous**. Each adapter calls its module, posts results, and returns. For a single module this is fine. For 29 modules in a real-time cognitive cycle, the slowest adapter determines cycle latency:

| Module | Typical latency | Blocking impact |
|--------|----------------|-----------------|
| IIT Φ (consciousness) | 50–500ms | Catastrophic for a sync cycle |
| VLA++ forward pass | 20–80ms | Significant |
| BCI EEG pipeline | ~4ms | Acceptable if async |
| Knowledge graph query | 1–10ms | Fine either way |
| Bio-inspired STDP | ~5ms/timestep | Fast per-tick, slow over epochs |

**Target cycle time**: < 100ms for real-time applications.  
**Conclusion**: modules must run **concurrently**, not sequentially.

---

## AsyncBlackboardAdapter

The proposed base class for async-native adapter integration:

```python
import asyncio
from abc import ABC, abstractmethod
from typing import Any

class AsyncBlackboardAdapter(ABC):
    """Base class for async Blackboard adapters.
    
    Subclass this and implement run_cycle_async(). Register with
    CognitiveCycleScheduler to run at the desired tick rate.
    """
    
    def __init__(self, blackboard: CognitiveBlackboard, module: Any):
        self.blackboard = blackboard
        self.module = module
        self._running = False
    
    @abstractmethod
    async def run_cycle_async(self) -> dict[str, Any]:
        """Compute module output.
        
        Returns a dict mapping Blackboard entry_type -> payload.
        Called at every tick. Should be non-blocking (use asyncio.to_thread
        for CPU-bound work).
        """
        ...
    
    async def post_results(self, results: dict[str, Any]) -> None:
        """Write results to the Blackboard (thread-safe via asyncio.to_thread)."""
        for entry_type, payload in results.items():
            await asyncio.to_thread(self.blackboard.post, entry_type, payload)
    
    async def start(self, interval_ms: float = 50.0) -> None:
        """Run this adapter in a continuous loop at interval_ms tick rate."""
        self._running = True
        while self._running:
            try:
                results = await self.run_cycle_async()
                if results:
                    await self.post_results(results)
            except Exception as exc:
                await asyncio.to_thread(
                    self.blackboard.post,
                    "adapter_error",
                    {"adapter": type(self).__name__, "error": str(exc), "ts": time.time()}
                )
            await asyncio.sleep(interval_ms / 1000.0)
    
    async def stop(self) -> None:
        """Gracefully stop this adapter's loop."""
        self._running = False
```

### Example: async consciousness adapter

```python
class AsyncConsciousnessAdapter(AsyncBlackboardAdapter):
    async def run_cycle_async(self) -> dict[str, Any]:
        # IIT Phi is CPU-bound — run in thread pool
        state = await asyncio.to_thread(self.module.compute)
        return {"consciousness_state": state}
```

### Example: async BCI adapter (high frequency)

```python
class AsyncBCIAdapter(AsyncBlackboardAdapter):
    async def run_cycle_async(self) -> dict[str, Any]:
        # EEG sampling — already async in hardware SDK
        frame = await self.module.read_frame_async()
        decoded = await asyncio.to_thread(self.module.decode, frame)
        return {
            "motor_imagery": decoded.motor_intent,
            "p300_event": decoded.p300,
        }
```

---

## CognitiveCycleScheduler

The multi-rate scheduler that runs all adapters concurrently:

```python
class CognitiveCycleScheduler:
    """Runs multiple AsyncBlackboardAdapters at different tick rates."""
    
    def __init__(self, blackboard: CognitiveBlackboard):
        self.blackboard = blackboard
        self._adapters: list[tuple[AsyncBlackboardAdapter, float]] = []
    
    def register(
        self,
        adapter: AsyncBlackboardAdapter,
        interval_ms: float,
    ) -> "CognitiveCycleScheduler":
        """Register an adapter with its desired tick interval. Chainable."""
        self._adapters.append((adapter, interval_ms))
        return self
    
    async def run(self) -> None:
        """Start all adapters. Runs until cancelled."""
        tasks = [
            asyncio.create_task(
                adapter.start(interval_ms),
                name=type(adapter).__name__,
            )
            for adapter, interval_ms in self._adapters
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            raise
```

### Recommended tick rates

| Module | Tick rate | Notes |
|--------|-----------|-------|
| `bci` | 4 ms | EEG at 250 Hz |
| `consciousness` | 100 ms | IIT Phi is expensive |
| `reasoning` | 50 ms | HybridReasoningEngine inference |
| `safety` | — | Middleware (see below), not polled |
| `bio_inspired` | 1000 ms | Circadian/sleep cycles are slow |
| `knowledge_graph` | on-demand | Query-driven |
| `rings` | 500 ms | P2P heartbeat |
| `knowledge_management` | 200 ms | Predictive synthesis |
| `quantum` | 500 ms | VQE/QAOA per-iteration |
| `vectordb` | on-demand | Semantic search triggered by events |

---

## Safety as Middleware (not a polled adapter)

The Safety module is special: it must **intercept Blackboard writes synchronously** for high-stakes entry types (action proposals, goal updates, agent directives). A polling model would allow unsafe entries to propagate during the gap between safety ticks.

Proposed: a `BlackboardMiddleware` interceptor pattern (separate from `AsyncBlackboardAdapter`):

```python
class SafetyMiddleware:
    """Synchronously gates Blackboard writes for safety-critical entry types."""
    
    GATED_TYPES = {"action_proposal", "goal_update", "agent_directive", "policy_change"}
    
    def __init__(self, safety_module, blackboard: CognitiveBlackboard):
        self.safety = safety_module
        # Monkey-patch or subclass Blackboard.post
        self._original_post = blackboard.post
        blackboard.post = self._intercepted_post
    
    def _intercepted_post(self, entry_type: str, payload: Any, **kwargs) -> None:
        if entry_type in self.GATED_TYPES:
            verdict = self.safety.verify(entry_type, payload)
            if not verdict.is_safe:
                self._original_post("safety_violation", {
                    "blocked_type": entry_type,
                    "reason": verdict.reason,
                })
                return  # Block the write
        self._original_post(entry_type, payload, **kwargs)
```

---

## Testing async adapters

Deterministic tests for async code require care:

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_consciousness_adapter_posts_to_blackboard():
    blackboard = MockBlackboard()
    module = MockConsciousnessModule(phi=0.42)
    adapter = AsyncConsciousnessAdapter(blackboard, module)
    
    # Run one tick
    results = await adapter.run_cycle_async()
    await adapter.post_results(results)
    
    assert blackboard.entries["consciousness_state"]["phi"] == 0.42

@pytest.mark.asyncio
async def test_scheduler_runs_all_adapters():
    blackboard = MockBlackboard()
    scheduler = CognitiveCycleScheduler(blackboard)
    
    adapter_a = MockAdapter(blackboard, name="A", result={"a": 1})
    adapter_b = MockAdapter(blackboard, name="B", result={"b": 2})
    
    scheduler.register(adapter_a, interval_ms=10)
    scheduler.register(adapter_b, interval_ms=20)
    
    # Run for 50ms, then cancel
    task = asyncio.create_task(scheduler.run())
    await asyncio.sleep(0.05)
    task.cancel()
    
    assert "a" in blackboard.entries
    assert "b" in blackboard.entries
```

---

## Open Questions

1. **Backpressure**: if BCI writes at 250 Hz but a subscriber is slower, drop stale or queue? Proposal: ring buffer of depth 1 for sensor types.
2. **Safety gating model**: middleware interceptor (above) vs. a priority-0 sync adapter?
3. **Error propagation**: degrade gracefully (skip missing entries) vs. pause cycle?
4. **CPU isolation**: should heavy modules (quantum, IIT Phi) run in a `ProcessPoolExecutor` instead of `asyncio.to_thread`?

---

## See Also

- [Integration Layer](Integration-Layer) — current sync adapter architecture
- [CognitiveCycle](CognitiveCycle) — full perception-to-action loop design
- [Cognitive Blackboard](Cognitive-Blackboard) — entry types, thread safety, EventBus
- [Safety Module](Safety-Module) — formal verification, EthicalVerificationEngine
