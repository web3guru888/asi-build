# Persistent Cognitive Memory — Phase 5.3

**Status**: Planning | **Issue**: [#186](https://github.com/web3guru888/asi-build/issues/186) | **Discussion**: [#189](https://github.com/web3guru888/asi-build/discussions/189)

Phase 5.3 gives ASI:BUILD persistent episodic memory: high-salience Blackboard events are consolidated into the Memgraph knowledge graph during the bio_inspired module's `SLEEP_PHASE`, so the agent remembers past experiences across CognitiveCycle restarts.

---

## Motivation

Today, the Cognitive Blackboard is ephemeral — entries expire via TTL and nothing survives a restart. Phase 5.3 changes this:

> "What the agent learns in one session should inform the next."

Episodic memory consolidation is inspired by biological memory: during sleep, the hippocampus (transient storage) replays high-salience experiences to the neocortex (long-term storage). ASI:BUILD's analog: Blackboard (transient) → MemoryConsolidator → Knowledge Graph (persistent).

---

## Architecture: Three-Layer Memory Stack

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Long-Term KG Memory                                │
│  Memgraph :Episode nodes with bi-temporal timestamps        │
│  Persists across restarts; indexed by salience + valid_from │
│  Queryable in PERCEPTION phase for context injection        │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: MemoryConsolidator Buffer                          │
│  deque(maxlen=1000) ring buffer (bounded memory pressure)   │
│  Populated during CyclePhase.INTEGRATION                   │
│  Flushed to KG during CyclePhase.SLEEP_PHASE               │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Cognitive Blackboard                               │
│  Ephemeral (no disk persistence)                           │
│  Source of truth during active ticks                       │
│  High-salience events promoted to Layer 2                  │
└─────────────────────────────────────────────────────────────┘
```

---

## EpisodicEvent Dataclass

```python
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class EpisodicEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    blackboard_key: str = ""
    value_snapshot: dict = field(default_factory=dict)
    salience: float = 0.0
    tick: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_module: str = ""
    consolidated: bool = False
```

---

## Salience Scoring

Salience determines what gets remembered. Uses `fnmatch` for wildcard pattern matching:

```python
import fnmatch

SALIENCE_REGISTRY: dict[str, float] = {
    "safety.weight_update_blocked": 1.0,
    "safety.verification_blocked":  1.0,
    "safety.verification_passed":   0.8,
    "goal.achieved":                0.9,
    "learning.new_association.*":   0.7,
    "stigmergy.coalition_accept.*": 0.75,
    "stigmergy.handoff.*":          0.65,
}

TEMPORAL_DECAY_PER_TICK: float = 0.05

ALWAYS_CONSOLIDATE_PATTERNS = [
    "safety.*blocked*",
    "safety.verification_blocked",
]

def compute_salience(key: str, age_ticks: int = 0) -> float:
    base = 0.1  # default for routine writes
    for pattern, score in SALIENCE_REGISTRY.items():
        if fnmatch.fnmatch(key, pattern):
            base = max(base, score)
    return max(0.0, base - age_ticks * TEMPORAL_DECAY_PER_TICK)

def always_consolidate(key: str) -> bool:
    return any(fnmatch.fnmatch(key, p) for p in ALWAYS_CONSOLIDATE_PATTERNS)
```

Events below salience 0.7 are filtered. Safety events (salience 1.0) are **always** consolidated regardless of buffer pressure.

---

## MemoryConsolidator

```python
from collections import deque

class MemoryConsolidator:
    """Consolidates high-salience Blackboard events into the Knowledge Graph
    during the bio_inspired SLEEP_PHASE."""

    SALIENCE_THRESHOLD: float = 0.7
    CONSOLIDATION_NAMESPACE: str = "memory.consolidation"
    EPISODE_BUFFER_MAX: int = 1000

    def __init__(self, blackboard, kg):
        self._blackboard = blackboard
        self._kg = kg
        self._buffer: deque[EpisodicEvent] = deque(maxlen=self.EPISODE_BUFFER_MAX)
        self._current_tick: int = 0

    async def tick(self, phase: CyclePhase, tick: int) -> None:
        self._current_tick = tick
        if phase == CyclePhase.INTEGRATION:
            await self._buffer_high_salience_events()
        elif phase == CyclePhase.SLEEP_PHASE:
            await self._consolidate_to_kg()

    async def _buffer_high_salience_events(self) -> None:
        entries = self._blackboard.query("*", limit=200)
        for entry in entries:
            salience = compute_salience(entry.key, age_ticks=0)
            if salience >= self.SALIENCE_THRESHOLD or always_consolidate(entry.key):
                self._buffer.append(EpisodicEvent(
                    blackboard_key=entry.key,
                    value_snapshot=dict(entry.value) if isinstance(entry.value, dict) else {"data": entry.value},
                    salience=salience,
                    tick=self._current_tick,
                    source_module=entry.key.split(".")[0],
                ))

    async def _consolidate_to_kg(self) -> None:
        consolidated = 0
        for event in list(self._buffer):
            if event.consolidated:
                continue
            approved = await self._safety_gate(event)
            if not approved:
                continue
            async with self._kg.transaction() as tx:
                tx.create_node(
                    label="Episode",
                    properties={
                        "event_id": event.event_id,
                        "blackboard_key": event.blackboard_key,
                        "salience": event.salience,
                        "tick": event.tick,
                        "valid_from": event.timestamp.isoformat(),
                        "transaction_time": datetime.now(tz=timezone.utc).isoformat(),
                        "source": event.source_module,
                    }
                )
            event.consolidated = True
            consolidated += 1
        self._blackboard.write(
            self.CONSOLIDATION_NAMESPACE,
            {"consolidated": consolidated, "tick": self._current_tick,
             "buffer_size": len(self._buffer)},
            ttl=3600,
        )
```

---

## SLEEP_PHASE Integration

`SLEEP_PHASE` is a new `CyclePhase` variant. The CognitiveCycle enters it when the bio_inspired module signals SLEEP state:

```python
class CyclePhase(str, Enum):
    PERCEPTION   = "PERCEPTION"
    REASONING    = "REASONING"
    ACTION       = "ACTION"
    LEARNING     = "LEARNING"      # Phase 5.1
    EVALUATION   = "EVALUATION"
    INTEGRATION  = "INTEGRATION"
    SLEEP_PHASE  = "SLEEP_PHASE"   # Phase 5.3
```

```python
# In CognitiveCycle.tick():
bio_state = blackboard.read("bio_inspired.cognitive_state")
if bio_state == "SLEEP":
    await self.run_phase(CyclePhase.SLEEP_PHASE)
    # MemoryConsolidator.tick(SLEEP_PHASE) flushes buffer → KG
```

No tick budget for `SLEEP_PHASE` — it runs during low-activity windows and is not latency-sensitive.

---

## Memory Retrieval in PERCEPTION

After consolidation, the CognitiveCycle retrieves relevant episodic memories at the start of each tick:

```python
# CognitiveCycle.PERCEPTION phase:
RETRIEVAL_WINDOW_HOURS = 24
RETRIEVAL_MIN_SALIENCE = 0.6
RETRIEVAL_LIMIT = 20

memories = await kg.query(
    "MATCH (e:Episode) "
    "WHERE e.salience >= $min_salience "
    "AND e.valid_from >= $cutoff "
    "RETURN e "
    "ORDER BY e.salience DESC "
    "LIMIT $limit",
    params={
        "min_salience": RETRIEVAL_MIN_SALIENCE,
        "cutoff": (datetime.now(tz=timezone.utc) - timedelta(hours=RETRIEVAL_WINDOW_HOURS)).isoformat(),
        "limit": RETRIEVAL_LIMIT,
    }
)
blackboard.write("memory.retrieved_episodes", memories, ttl=100)
```

Modules in the REASONING phase can read `memory.retrieved_episodes` to inform inference. The knowledge graph is indexed on `(salience, valid_from)` for efficient retrieval.

---

## Safety Audit Trail

Safety events receive special treatment:

1. `safety.*blocked*` and `safety.verification_blocked` entries always have salience 1.0
2. They are always consolidated (bypass buffer eviction)
3. Recommendation: mark them read-only in the KG to prevent tampering

```python
SAFETY_AUDIT_LABELS = ["Episode", "SafetyAudit"]  # dual-label for KG queries
```

This ensures the safety audit trail survives across restarts and is auditable without relying on ephemeral Blackboard state.

---

## Acceptance Criteria

From [Issue #186](https://github.com/web3guru888/asi-build/issues/186):

- [ ] `EpisodicEvent` dataclass with `event_id`, `blackboard_key`, `salience`, `tick`, `timestamp`, `consolidated`
- [ ] `MemoryConsolidator.tick()` phase-dispatched from CognitiveCycle
- [ ] `_buffer_high_salience_events()`: ring buffer, max 1000 events
- [ ] `_consolidate_to_kg()`: bi-temporal KG writes, `:Episode` node schema
- [ ] `compute_salience()`: 6+ signal types, `fnmatch` wildcard matching, temporal decay
- [ ] `always_consolidate()`: safety events always consolidated
- [ ] `CyclePhase.SLEEP_PHASE`: bio_inspired gating in CognitiveCycle
- [ ] Memory retrieval: `memory.retrieved_episodes` Blackboard write in PERCEPTION
- [ ] Memory survives CognitiveCycle restart (KG persistent; Blackboard ephemeral)
- [ ] Safety gating: EthicalVerificationEngine blocked → episode NOT consolidated
- [ ] 10+ tests: buffer overflow, salience threshold, KG write, retrieval, safety block, sleep-wake cycle

---

## Dependencies

| Dependency | Why |
|-----------|-----|
| [#181 Phase 5.1 Online Learning](https://github.com/web3guru888/asi-build/issues/181) | KG transaction patterns established |
| [#185 Phase 5.2 Emergent Coordination](https://github.com/web3guru888/asi-build/issues/185) | Coalition events are high-salience consolidation candidates |
| [#164 Production Deployment](https://github.com/web3guru888/asi-build/issues/164) | Persistent Memgraph backend required |
| [#46 Bio-inspired CognitiveState](https://github.com/web3guru888/asi-build/issues/46) | SLEEP_PHASE state signal source |

---

## Related

- [Discussion #184: SLEEP_PHASE Q&A](https://github.com/web3guru888/asi-build/discussions/184)
- [Discussion #189: Show & Tell — MemoryConsolidator design](https://github.com/web3guru888/asi-build/discussions/189)
- [Discussion #190: Ideas — static vs. learned salience model](https://github.com/web3guru888/asi-build/discussions/190)
- [Issue #176: Phase 5 milestone overview](https://github.com/web3guru888/asi-build/issues/176)
- [Phase 5 Roadmap wiki](https://github.com/web3guru888/asi-build/wiki/Phase-5-Roadmap)
- [Knowledge Graph wiki](https://github.com/web3guru888/asi-build/wiki/Knowledge-Graph)
- [Bio-Inspired wiki](https://github.com/web3guru888/asi-build/wiki/Bio-Inspired)
