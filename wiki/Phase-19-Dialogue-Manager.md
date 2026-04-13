# Phase 19.2 — DialogueManager

> **Status**: 🟡 Spec'd  
> **Issue**: #469  
> **Depends on**: Phase 19.1 SemanticParser  
> **Produces**: `DialogueState` consumed by Phase 19.3 ResponseGenerator  

---

## Overview

`DialogueManager` maintains conversation state across multiple turns, tracking dialogue acts, slot accumulation, context windows, and turn history for coherent multi-turn interactions. In any agent-facing or user-facing NLU pipeline the dialogue manager sits between the parser (which extracts a single-turn `SemanticFrame`) and the response generator (which needs the **full conversation context** to produce appropriate replies).

Core responsibilities:

| Concern | Mechanism |
|---|---|
| **Turn tracking** | Append each user/system/agent turn with a unique `turn_id`, timestamp, and dialogue act classification |
| **Slot accumulation** | Carry forward slot values across turns so the user never has to repeat information (latest-wins merge) |
| **Context windowing** | Keep only the most recent *N* turns visible to downstream consumers, bounding memory and token cost |
| **Intent continuity** | Track the `active_intent` and update it only when the parser signals a clear intent switch |
| **Session lifecycle** | Create, timeout, and garbage-collect sessions so stale conversations don't leak memory |
| **Auto-clarification** | When the parser returns a low-confidence frame, the manager automatically inserts a CLARIFY turn |

---

## Enums

### DialogueAct

Dialogue acts categorise the **communicative function** of each turn, independent of its surface text.

```python
class DialogueAct(str, Enum):
    INFORM   = "inform"
    REQUEST  = "request"
    CONFIRM  = "confirm"
    DENY     = "deny"
    GREET    = "greet"
    FAREWELL = "farewell"
    CLARIFY  = "clarify"
    COMMAND  = "command"
    QUERY    = "query"
    ACKNOWLEDGE = "acknowledge"
```

| Act | Description | Example |
|---|---|---|
| `INFORM` | User/agent supplies a new piece of information | *"My name is Alice."* |
| `REQUEST` | Asks for information or an action | *"What is the weather tomorrow?"* |
| `CONFIRM` | Affirms a proposition | *"Yes, that's correct."* |
| `DENY` | Rejects or negates a proposition | *"No, I said London, not Paris."* |
| `GREET` | Session-opening pleasantry | *"Hello!"* |
| `FAREWELL` | Session-closing signal | *"Goodbye."* |
| `CLARIFY` | Requests disambiguation (often system-generated) | *"Did you mean London, UK or London, Ontario?"* |
| `COMMAND` | Imperative instruction | *"Book the 3 PM flight."* |
| `QUERY` | Structured data retrieval request | *"Show me all open tickets."* |
| `ACKNOWLEDGE` | Back-channel signal; no new content | *"Got it."* / *"OK."* |

### TurnRole

```python
class TurnRole(str, Enum):
    USER   = "user"
    SYSTEM = "system"
    AGENT  = "agent"
```

| Role | Semantics |
|---|---|
| `USER` | External human or calling application |
| `SYSTEM` | Platform-level messages (timeouts, errors, injected context) |
| `AGENT` | The ASI-Build agent pipeline itself |

---

## Data Structures

All structures are **frozen dataclasses** (`@dataclass(frozen=True, slots=True)`).

### DialogueTurn

```python
@dataclass(frozen=True, slots=True)
class DialogueTurn:
    turn_id:      str                        # UUIDv4
    role:         TurnRole
    act:          DialogueAct
    text:         str                        # raw utterance
    frame:        dict[str, Any] | None      # SemanticFrame dict from parser (None for SYSTEM turns)
    timestamp_ns: int                        # monotonic_ns at ingestion
    metadata:     MappingProxyType[str, Any] # immutable extra payload
```

### DialogueState

```python
@dataclass(frozen=True, slots=True)
class DialogueState:
    session_id:        str                          # UUIDv4
    turns:             tuple[DialogueTurn, ...]      # full turn history (immutable snapshot)
    accumulated_slots: MappingProxyType[str, Any]    # merged slot dict (latest-wins)
    active_intent:     str | None                    # current intent label or None
    context_window:    tuple[DialogueTurn, ...]      # last N turns (sliding)
    max_turns:         int                           # context window size
    created_ns:        int
    updated_ns:        int
```

### DialogueConfig

```python
@dataclass(frozen=True, slots=True)
class DialogueConfig:
    max_history:       int   = 200          # total turns kept before oldest are pruned
    context_window:    int   = 10           # turns visible in context_window slice
    slot_carry_over:   bool  = True         # carry slots across turns (latest-wins)
    auto_clarify:      bool  = True         # insert CLARIFY turn on low-confidence frames
    session_timeout_s: float = 1800.0       # 30 min idle → session evicted
```

---

## Protocol

```python
@runtime_checkable
class DialogueManager(Protocol):

    async def new_session(self, *, session_id: str | None = None) -> str:
        """Create a new dialogue session. Returns session_id (generated if not supplied)."""
        ...

    async def add_turn(
        self,
        session_id: str,
        role: TurnRole,
        text: str,
        frame: dict[str, Any] | None = None,
        act: DialogueAct | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DialogueTurn:
        """Append a turn to the session. If *act* is None, infer from frame/text heuristics."""
        ...

    async def get_state(self, session_id: str) -> DialogueState:
        """Return the current frozen DialogueState snapshot."""
        ...

    async def get_context(self, session_id: str) -> tuple[DialogueTurn, ...]:
        """Shorthand: return only the context_window slice."""
        ...

    async def clear_session(self, session_id: str) -> bool:
        """Destroy a session. Returns True if it existed."""
        ...

    async def active_sessions(self) -> frozenset[str]:
        """Return the set of all live session IDs."""
        ...
```

---

## Implementation — `InMemoryDialogueManager`

```python
class InMemoryDialogueManager:
    """Production implementation backed by an in-memory dict."""

    def __init__(self, config: DialogueConfig | None = None) -> None:
        self._config = config or DialogueConfig()
        self._sessions: dict[str, _MutableSession] = {}
        self._lock = asyncio.Lock()
        self._gc_task: asyncio.Task[None] | None = None
```

### Key Internals

| Component | Detail |
|---|---|
| **`_sessions`** | `dict[str, _MutableSession]` — mutable working copy; `get_state()` returns a frozen snapshot |
| **`asyncio.Lock`** | Serialises all mutations; read-only `get_context()` takes the lock to ensure snapshot consistency |
| **`_infer_act(text, frame)`** | If caller omits `act`, heuristics infer it: `frame.intent == "confirm" → CONFIRM`, question-mark text → `QUERY`, etc. Falls back to `INFORM` |
| **Slot carry-over** | When `slot_carry_over=True`, `add_turn()` merges `frame["slots"]` into `accumulated_slots` using **latest-wins**: new values overwrite old ones for the same key, existing keys not present in the new frame are preserved |
| **Context window** | `context_window = turns[-config.context_window:]` — a sliding tail slice recomputed on every `add_turn()` call |
| **Auto-clarify** | When `auto_clarify=True` and `frame["confidence"] < 0.4`, `add_turn()` automatically appends a second `AGENT/CLARIFY` turn after the user turn, asking for disambiguation |
| **History pruning** | If `len(turns) > max_history`, the oldest turns beyond the limit are dropped (FIFO). Accumulated slots are **not** lost since they live in a separate dict |
| **Session timeout** | Background `_gc_loop` runs every 60 s, evicts sessions whose `updated_ns` is older than `session_timeout_s` |

### Auto-Clarify Logic

```
if auto_clarify and frame and frame.get("confidence", 1.0) < 0.4:
    clarify_turn = DialogueTurn(
        turn_id=uuid4().hex,
        role=TurnRole.AGENT,
        act=DialogueAct.CLARIFY,
        text=f"I'm not sure I understood. Could you rephrase or clarify: {frame.get('raw', text)!r}?",
        frame=None,
        timestamp_ns=time.monotonic_ns(),
        metadata=MappingProxyType({"auto": True}),
    )
    session.turns.append(clarify_turn)
```

### Session Timeout GC

```python
async def _gc_loop(self) -> None:
    while True:
        await asyncio.sleep(60)
        now = time.monotonic_ns()
        cutoff = now - int(self._config.session_timeout_s * 1e9)
        async with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.updated_ns < cutoff]
            for sid in expired:
                del self._sessions[sid]
                SESSIONS_EVICTED.inc()
```

---

## Implementation — `NullDialogueManager`

No-op implementation for testing and placeholder injection.

```python
class NullDialogueManager:
    async def new_session(self, *, session_id=None) -> str:
        return session_id or uuid4().hex

    async def add_turn(self, session_id, role, text, frame=None, act=None, metadata=None) -> DialogueTurn:
        return DialogueTurn(turn_id=uuid4().hex, role=role, act=act or DialogueAct.ACKNOWLEDGE,
                            text=text, frame=frame, timestamp_ns=0, metadata=MappingProxyType({}))

    async def get_state(self, session_id) -> DialogueState:
        return DialogueState(session_id=session_id, turns=(), accumulated_slots=MappingProxyType({}),
                             active_intent=None, context_window=(), max_turns=10, created_ns=0, updated_ns=0)

    async def get_context(self, session_id) -> tuple[DialogueTurn, ...]:
        return ()

    async def clear_session(self, session_id) -> bool:
        return False

    async def active_sessions(self) -> frozenset[str]:
        return frozenset()
```

---

## Factory

```python
def make_dialogue_manager(
    config: DialogueConfig | None = None,
) -> DialogueManager:
    """Construct the default DialogueManager implementation."""
    return InMemoryDialogueManager(config=config)
```

---

## Data Flow

```
  ┌──────────┐       SemanticFrame        ┌──────────────────┐
  │ Semantic  │──────────────────────────▶│  DialogueManager  │
  │ Parser    │  {intent, slots, conf}    │                    │
  │ (19.1)    │                            │  ┌──────────────┐ │
  └──────────┘                            │  │ add_turn()   │ │
                                           │  └──────┬───────┘ │
  User text ──────────────────────────────▶│         │          │
                                           │  ┌──────▼───────┐ │
                                           │  │ _infer_act() │ │
                                           │  └──────┬───────┘ │
                                           │         │          │
                                           │  ┌──────▼───────┐ │
                                           │  │ Slot merge   │ │
                                           │  │ (latest-wins)│ │
                                           │  └──────┬───────┘ │
                                           │         │          │
                                           │  ┌──────▼───────┐ │
                                           │  │ Auto-clarify │ │
                                           │  │ check (< 0.4)│ │
                                           │  └──────┬───────┘ │
                                           │         │          │
                                           │  ┌──────▼───────┐ │
                                           │  │ Context      │ │
                                           │  │ window slide │ │
                                           │  └──────┬───────┘ │
                                           └─────────┼──────────┘
                                                     │
                                           DialogueState snapshot
                                                     │
                                                     ▼
                                           ┌──────────────────┐
                                           │ ResponseGenerator │
                                           │ (19.3)            │
                                           └──────────────────┘
```

### Multi-Turn Slot Accumulation Example

```
Turn 1 (USER/INFORM):  "Book a flight to London"
  → frame.slots = {destination: "London"}
  → accumulated = {destination: "London"}

Turn 2 (AGENT/CLARIFY): "When would you like to travel?"
  → accumulated = {destination: "London"}  (unchanged)

Turn 3 (USER/INFORM):  "Next Friday, economy class"
  → frame.slots = {date: "next_friday", class: "economy"}
  → accumulated = {destination: "London", date: "next_friday", class: "economy"}

Turn 4 (USER/DENY):   "Actually, make it business class"
  → frame.slots = {class: "business"}
  → accumulated = {destination: "London", date: "next_friday", class: "business"}
```

---

## Integration Points

### ← SemanticParser (Phase 19.1)

`SemanticParser.parse()` returns a `SemanticFrame` dict containing `intent`, `slots`, `confidence`, and `raw`. This dict is passed directly to `add_turn(frame=...)`. The dialogue manager does **not** call the parser itself — the NLU pipeline orchestrator is responsible for sequencing.

### → ResponseGenerator (Phase 19.3)

`ResponseGenerator` consumes a `DialogueState` to produce context-aware replies. It reads:
- `context_window` — the turns the LLM/template engine should see
- `accumulated_slots` — the filled slot map for template rendering
- `active_intent` — to select the response strategy

### ↔ CollaborationChannel (Phase 12.3)

For inter-agent dialogue, `CollaborationChannel` wraps `DialogueManager` sessions:
- Each agent pair shares a `session_id`
- Turns are tagged with `TurnRole.AGENT` and `metadata={"agent_id": ...}`
- Slot carry-over enables agents to build shared understanding across rounds

### ↔ CausalMemoryIndex (Phase 18.4)

Completed dialogue sessions can be indexed by `CausalMemoryIndex` for long-term retrieval:
- `DialogueState.turns` are serialised and stored as causal chains
- Slot accumulation maps become queryable memory fragments

---

## Prometheus Metrics

```python
TURNS_ADDED = Counter(
    "asi_dialogue_turns_added_total",
    "Total turns appended across all sessions",
    ["role", "act"],
)
ACTIVE_SESSIONS = Gauge(
    "asi_dialogue_active_sessions",
    "Number of live dialogue sessions",
)
SESSIONS_CREATED = Counter(
    "asi_dialogue_sessions_created_total",
    "Total sessions created",
)
SESSIONS_EVICTED = Counter(
    "asi_dialogue_sessions_evicted_total",
    "Sessions evicted by timeout GC",
)
CLARIFY_INJECTED = Counter(
    "asi_dialogue_clarify_injected_total",
    "Auto-clarify turns injected due to low confidence",
)
```

| Metric | PromQL Example | Purpose |
|---|---|---|
| `asi_dialogue_turns_added_total` | `rate(asi_dialogue_turns_added_total[5m])` | Turn throughput per role/act |
| `asi_dialogue_active_sessions` | `asi_dialogue_active_sessions` | Live session count for capacity planning |
| `asi_dialogue_sessions_created_total` | `increase(asi_dialogue_sessions_created_total[1h])` | Session creation rate |
| `asi_dialogue_sessions_evicted_total` | `increase(asi_dialogue_sessions_evicted_total[1h])` | Timeout rate — tune `session_timeout_s` |
| `asi_dialogue_clarify_injected_total` | `rate(asi_dialogue_clarify_injected_total[5m])` | Clarify frequency — signals parser quality issues |

### Grafana Alert

```yaml
- alert: HighClarifyRate
  expr: rate(asi_dialogue_clarify_injected_total[10m]) / rate(asi_dialogue_turns_added_total{role="user"}[10m]) > 0.3
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: ">30% of user turns trigger auto-clarify — parser may need retraining"
```

---

## Test Targets (12)

| # | Test | Assertion |
|---|---|---|
| 1 | `test_new_session_returns_uuid` | `new_session()` returns a valid hex UUID string |
| 2 | `test_add_turn_appends_to_history` | After `add_turn()`, `get_state().turns` length increases by 1 |
| 3 | `test_slot_carry_over_latest_wins` | Slot `class: economy` then `class: business` → accumulated `class == "business"` |
| 4 | `test_slot_carry_over_preserves_existing` | Slot `dest: London` then `date: friday` → accumulated has both keys |
| 5 | `test_slot_carry_over_disabled` | `slot_carry_over=False` → accumulated_slots always empty |
| 6 | `test_context_window_slides` | After 15 turns with `context_window=10`, `get_context()` returns exactly 10 |
| 7 | `test_auto_clarify_injects_turn` | Frame `{"confidence": 0.2}` → next turn in history is `AGENT/CLARIFY` |
| 8 | `test_auto_clarify_disabled` | `auto_clarify=False` → no CLARIFY turn injected regardless of confidence |
| 9 | `test_session_timeout_gc` | Session idle beyond `session_timeout_s` → `active_sessions()` no longer contains it |
| 10 | `test_clear_session_removes` | `clear_session(sid)` → `get_state(sid)` raises `KeyError` |
| 11 | `test_infer_act_question_mark` | Text ending in `?` with no explicit act → inferred as `QUERY` |
| 12 | `test_null_dialogue_manager_noop` | `NullDialogueManager` satisfies `DialogueManager` Protocol and returns defaults |

### Sample Test Skeleton

```python
@pytest.mark.asyncio
async def test_slot_carry_over_latest_wins():
    mgr = make_dialogue_manager(DialogueConfig(slot_carry_over=True))
    sid = await mgr.new_session()
    await mgr.add_turn(sid, TurnRole.USER, "Economy to London",
                        frame={"slots": {"dest": "London", "class": "economy"}, "confidence": 0.9})
    await mgr.add_turn(sid, TurnRole.USER, "Make it business",
                        frame={"slots": {"class": "business"}, "confidence": 0.95})
    state = await mgr.get_state(sid)
    assert state.accumulated_slots["dest"] == "London"
    assert state.accumulated_slots["class"] == "business"


@pytest.mark.asyncio
async def test_auto_clarify_injects_turn():
    mgr = make_dialogue_manager(DialogueConfig(auto_clarify=True))
    sid = await mgr.new_session()
    await mgr.add_turn(sid, TurnRole.USER, "mumble mumble",
                        frame={"slots": {}, "confidence": 0.2, "raw": "mumble mumble"})
    state = await mgr.get_state(sid)
    assert len(state.turns) == 2  # user turn + auto-clarify
    assert state.turns[-1].act == DialogueAct.CLARIFY
    assert state.turns[-1].role == TurnRole.AGENT
```

---

## Implementation Order (14 Steps)

| Step | Task | LoC (est.) |
|---|---|---|
| 1 | Define `DialogueAct` enum in `enums.py` | 15 |
| 2 | Define `TurnRole` enum in `enums.py` | 8 |
| 3 | Define `DialogueTurn` frozen dataclass | 20 |
| 4 | Define `DialogueState` frozen dataclass | 25 |
| 5 | Define `DialogueConfig` frozen dataclass with defaults | 15 |
| 6 | Define `DialogueManager` Protocol with 6 methods | 30 |
| 7 | Implement `_MutableSession` internal helper class | 35 |
| 8 | Implement `InMemoryDialogueManager.__init__` + `new_session()` | 25 |
| 9 | Implement `add_turn()` with `_infer_act()` heuristics | 60 |
| 10 | Implement slot carry-over merge logic in `add_turn()` | 30 |
| 11 | Implement auto-clarify injection in `add_turn()` | 25 |
| 12 | Implement `_gc_loop` background task + `start()`/`stop()` | 40 |
| 13 | Implement `NullDialogueManager` | 30 |
| 14 | Implement `make_dialogue_manager()` factory + register Prometheus metrics | 20 |
| | **Total** | **~378** |

---

## mypy Strict Compliance

| Pattern | Narrowing |
|---|---|
| `frame: dict[str, Any] \| None` | `if frame is not None:` before slot access |
| `act: DialogueAct \| None` | `act = act or self._infer_act(text, frame)` — always resolves to `DialogueAct` |
| `session_id: str \| None` | `session_id = session_id or uuid4().hex` in `new_session()` |
| `metadata: dict \| None` | `MappingProxyType(metadata or {})` wraps to immutable |
| `_sessions[sid]` | `KeyError` propagates naturally; callers handle |

---

## Phase 19 Sub-phase Tracker

| # | Sub-phase | Component | Issue | Wiki | Status |
|---|---|---|---|---|---|
| 19.1 | Semantic Parsing | `SemanticParser` | #466 | ✅ | 🟡 Spec'd |
| 19.2 | Dialogue Management | `DialogueManager` | #469 | ✅ | 🟡 Spec'd |
| 19.3 | Response Generation | `ResponseGenerator` | — | — | ⬚ Planned |
| 19.4 | Sentiment Analysis | `SentimentAnalyser` | — | — | ⬚ Planned |
| 19.5 | NLU Orchestrator | `NLUOrchestrator` | — | — | ⬚ Planned |

---

*Last updated: 2026-04-13 — Phase 19.2 DialogueManager spec complete*
