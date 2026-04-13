# Phase 19.1 — SemanticParser

> **Status**: 🟡 Spec'd  
> **Issue**: [#466](https://github.com/web3guru888/asi-build/issues/466)  
> **Module path**: `asi.nlp.semantic_parser`  
> **Since**: v0.19.0  

---

## Overview

The **SemanticParser** converts raw natural-language input (from users, peer agents, or sensor descriptions) into structured **SemanticFrames** — typed records carrying an `intent` label, a confidence score, and zero-or-more typed **Slots** (named parameters extracted from the utterance). Downstream components never touch free text directly; they act exclusively on SemanticFrames.

### Design Rationale

1. **Separation of concerns** — Parsing is inherently noisy; isolating it behind a Protocol lets the rest of the cognitive pipeline assume structured input.
2. **Swappable backends** — A regex-based rule engine ships by default (zero external deps), but the Protocol/Factory pattern lets teams drop in transformer-backed parsers, LLM extractors, or hybrid pipelines without rewiring callers.
3. **Batch efficiency** — `parse_batch()` exposes a vectorisable path so GPU-backed parsers can amortise overhead across multiple utterances per cycle.
4. **Extensibility** — `register_pattern()` allows runtime registration of new intent patterns without redeployment, supporting hot-loaded custom domains.

---

## Enums

### IntentConfidence

Tri-level confidence bucketing derived from the raw float score:

| Member   | Threshold     | Semantics |
|----------|---------------|-----------|
| `HIGH`   | score ≥ 0.85  | High certainty — safe to auto-dispatch |
| `MEDIUM` | 0.60 ≤ score < 0.85 | Moderate certainty — may require confirmation |
| `LOW`    | score < 0.60  | Low certainty — route to fallback or clarification |

```python
class IntentConfidence(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @staticmethod
    def from_score(score: float) -> "IntentConfidence":
        if score >= 0.85:
            return IntentConfidence.HIGH
        if score >= 0.60:
            return IntentConfidence.MEDIUM
        return IntentConfidence.LOW
```

### SlotType

Semantic type tag for extracted slot values:

| Member     | Example Value          | Notes |
|------------|------------------------|-------|
| `ENTITY`   | `"Berlin"`, `"Alice"` | Named entities — persons, orgs, products |
| `NUMBER`   | `42`, `3.14`          | Numeric literals (int or float) |
| `DATE`     | `"2026-04-13"`        | ISO-8601 date strings |
| `DURATION` | `"PT30M"`, `"2h"`     | ISO-8601 duration or human shorthand |
| `LOCATION` | `"lat:52.52,lon:13.4"`| Geocoded or textual location |
| `CUSTOM`   | *(any)*               | Catch-all for domain-specific types |

```python
class SlotType(enum.Enum):
    ENTITY = "entity"
    NUMBER = "number"
    DATE = "date"
    DURATION = "duration"
    LOCATION = "location"
    CUSTOM = "custom"
```

---

## Data Structures

### `Slot` (frozen dataclass)

A single extracted parameter from the utterance.

| Field        | Type                | Default   | Description |
|--------------|---------------------|-----------|-------------|
| `name`       | `str`               | —         | Slot label (e.g. `"destination"`, `"count"`) |
| `value`      | `Any`               | —         | Extracted value (str, int, float, datetime…) |
| `slot_type`  | `SlotType`          | —         | Semantic type tag |
| `confidence` | `float`             | `1.0`     | Per-slot confidence ∈ [0, 1] |
| `span`       | `tuple[int, int]`   | `(0, 0)`  | Character offset `(start, end)` in raw text |

```python
@dataclass(frozen=True, slots=True)
class Slot:
    name: str
    value: Any
    slot_type: SlotType
    confidence: float = 1.0
    span: tuple[int, int] = (0, 0)
```

### `SemanticFrame` (frozen dataclass)

The structured output of a single parse.

| Field              | Type                       | Default   | Description |
|--------------------|----------------------------|-----------|-------------|
| `intent`           | `str`                      | —         | Canonical intent label (e.g. `"navigate"`, `"query_status"`) |
| `confidence`       | `float`                    | —         | Raw confidence score ∈ [0, 1] |
| `confidence_level` | `IntentConfidence`         | —         | Bucketed level derived from `confidence` |
| `slots`            | `tuple[Slot, ...]`         | `()`      | Extracted slots, ordered by span offset |
| `raw_text`         | `str`                      | `""`      | Original input text for audit / replay |
| `timestamp_ns`     | `int`                      | `0`       | `time.time_ns()` at parse start |

```python
@dataclass(frozen=True, slots=True)
class SemanticFrame:
    intent: str
    confidence: float
    confidence_level: IntentConfidence
    slots: tuple[Slot, ...] = ()
    raw_text: str = ""
    timestamp_ns: int = 0
```

**Invariant**: `confidence_level == IntentConfidence.from_score(confidence)` — enforced by the factory classmethod.

### `ParserConfig` (frozen dataclass)

| Field                  | Type                    | Default               | Description |
|------------------------|-------------------------|-----------------------|-------------|
| `model_backend`        | `str`                   | `"rule_based"`        | Backend selector: `"rule_based"`, `"transformer"`, `"llm"` |
| `confidence_threshold` | `float`                 | `0.30`                | Below this score → `fallback_intent` |
| `max_slots`            | `int`                   | `16`                  | Cap on extracted slots per frame |
| `fallback_intent`      | `str`                   | `"unknown"`           | Intent label when no pattern matches or confidence is too low |
| `custom_patterns`      | `dict[str, str]`        | `field(default_factory=dict)` | Intent→regex mappings loaded at init |

```python
@dataclass(frozen=True)
class ParserConfig:
    model_backend: str = "rule_based"
    confidence_threshold: float = 0.30
    max_slots: int = 16
    fallback_intent: str = "unknown"
    custom_patterns: dict[str, str] = field(default_factory=dict)
```

---

## Protocol

```python
@runtime_checkable
class SemanticParser(Protocol):
    async def parse(self, text: str) -> SemanticFrame:
        """Parse a single utterance into a SemanticFrame."""
        ...

    async def parse_batch(self, texts: Sequence[str]) -> list[SemanticFrame]:
        """Parse multiple utterances. Implementations MAY parallelise."""
        ...

    def register_pattern(self, intent: str, pattern: str, *, priority: int = 0) -> None:
        """Register a regex pattern for an intent at runtime.
        Higher priority patterns are tried first."""
        ...

    def get_intents(self) -> frozenset[str]:
        """Return all registered intent labels (frozen snapshot)."""
        ...
```

### Contract Notes

| Method             | Must be async? | Idempotent? | Thread-safe? |
|--------------------|----------------|-------------|--------------|
| `parse()`          | Yes            | Yes         | Via asyncio.Lock |
| `parse_batch()`    | Yes            | Yes         | Via asyncio.Lock |
| `register_pattern()` | No          | Yes (overwrite) | Guarded by lock |
| `get_intents()`    | No             | Yes         | Returns frozen copy |

---

## Implementation: `RuleBasedSemanticParser`

The default shipped parser — zero external dependencies, entirely regex-driven.

### Architecture

```
                ┌──────────────────────────────────────────┐
                │         RuleBasedSemanticParser           │
                │                                          │
 raw text ──►   │  1. _tokenize(text)                      │
                │     └─ lowercase, strip, unicode norm     │
                │                                          │
                │  2. _match_patterns(tokens)               │
                │     └─ iterate by descending priority     │
                │     └─ first full match wins              │
                │     └─ capture groups → raw slots         │
                │                                          │
                │  3. _extract_slots(raw_slots, text)       │
                │     └─ infer SlotType per capture group   │
                │     └─ DATE regex → SlotType.DATE         │
                │     └─ numeric regex → SlotType.NUMBER    │
                │     └─ duration regex → SlotType.DURATION │
                │     └─ else → SlotType.ENTITY             │
                │     └─ cap at max_slots                   │
                │                                          │
                │  4. _score(match, text) → float           │
                │     └─ coverage ratio: matched_chars /    │
                │        total_chars × priority_boost       │
                │     └─ clamp to [0.0, 1.0]               │
                │                                          │
                │  5. Build SemanticFrame                   │
                │     └─ if score < threshold → fallback    │
                │     └─ attach slots, timestamp, raw_text  │
                └──────────────────────────────────────────┘
```

### Internal State

| Attribute         | Type                                           | Description |
|-------------------|------------------------------------------------|-------------|
| `_patterns`       | `SortedList[tuple[int, str, re.Pattern]]`      | `(-priority, intent, compiled_regex)` — descending priority |
| `_intent_set`     | `set[str]`                                     | Mutable intent label set; `get_intents()` returns `frozenset(self._intent_set)` |
| `_config`         | `ParserConfig`                                 | Immutable config |
| `_lock`           | `asyncio.Lock`                                 | Guards `_patterns` and `_intent_set` mutations |
| `_slot_infer_re`  | `dict[SlotType, re.Pattern]`                   | Pre-compiled regexes for slot type inference |

### Confidence Scoring Algorithm

```
coverage = sum(len(group) for group in match.groups()) / max(len(text), 1)
priority_boost = 1.0 + (priority / 100.0)   # priority 0→1.0, 10→1.1, 50→1.5
raw_score = min(coverage * priority_boost, 1.0)
```

If `raw_score < config.confidence_threshold`, the parser returns a frame with `intent = config.fallback_intent` and `confidence = raw_score`.

### Slot Type Inference Rules

| Regex Pattern (applied to value) | Inferred SlotType |
|----------------------------------|-------------------|
| `^\d{4}-\d{2}-\d{2}(T.*)?$`    | `DATE`            |
| `^P(\d+[YMWD])*T?(\d+[HMS])*$` | `DURATION`        |
| `^-?\d+(\.\d+)?$`               | `NUMBER`          |
| `^(lat|lon|geo):` or known gazetteer | `LOCATION`   |
| *(fallback)*                     | `ENTITY`          |

### `parse_batch()` Strategy

Default implementation uses `asyncio.gather(*[self.parse(t) for t in texts])`. GPU-backed subclasses can override this with true batch inference.

---

## Implementation: `NullSemanticParser`

No-op implementation for testing and stub pipelines:

- `parse()` → `SemanticFrame(intent="null", confidence=0.0, confidence_level=LOW)`
- `parse_batch()` → `[parse(t) for t in texts]`
- `register_pattern()` → no-op
- `get_intents()` → `frozenset()`

---

## Factory

```python
def make_semantic_parser(config: ParserConfig | None = None) -> SemanticParser:
    """Construct a SemanticParser from config.

    Returns:
        RuleBasedSemanticParser  if config.model_backend == "rule_based" (default)
        NullSemanticParser       if config.model_backend == "null"
    Raises:
        ValueError for unknown backends
    """
    cfg = config or ParserConfig()
    if cfg.model_backend == "rule_based":
        return RuleBasedSemanticParser(cfg)
    if cfg.model_backend == "null":
        return NullSemanticParser()
    raise ValueError(f"Unknown parser backend: {cfg.model_backend!r}")
```

The factory pre-loads `config.custom_patterns` via `register_pattern()` after construction.

---

## Data Flow

```
                          ┌──────────────────────┐
    User / Agent          │   SemanticParser      │      Downstream
    Utterance             │   (RuleBased /        │      Consumers
                          │    Transformer)       │
  "Navigate to Berlin     │                       │
   in 30 minutes"  ──────►  parse(text)           │
                          │    │                   │
                          │    ├─ tokenize         │
                          │    ├─ pattern match    │
                          │    ├─ slot extract     │
                          │    ├─ score            │
                          │    ▼                   │
                          │  SemanticFrame(        │
                          │   intent="navigate",   │──────► DialogueManager 19.2
                          │   confidence=0.91,     │──────► GoalRegistry 10.1
                          │   confidence_level=HIGH│──────► CognitiveCycle
                          │   slots=(              │
                          │     Slot("destination",│
                          │       "Berlin",ENTITY),│
                          │     Slot("eta","PT30M",│
                          │       DURATION)),      │
                          │   raw_text="Navigate…",│
                          │   timestamp_ns=…       │
                          │  )                     │
                          └──────────────────────┘
```

---

## Integration Map

### Outbound (SemanticParser produces)

| Consumer                  | Phase | Data Exchanged | Notes |
|---------------------------|-------|----------------|-------|
| **DialogueManager**       | 19.2  | `SemanticFrame` | Primary consumer — routes intents to dialogue states |
| **GoalRegistry**          | 10.1  | `SemanticFrame` with `COMMAND` intents | Creates goals from parsed commands |
| **CognitiveCycle**        | Core  | `SemanticFrame` via Blackboard entry | Posted as `"nlp.semantic_frame"` key |
| **SafetyFilter**          | 11.1  | `SemanticFrame` | Pre-execution safety check on parsed intents |

### Inbound (SemanticParser consumes)

| Producer                  | Phase | Data Exchanged | Notes |
|---------------------------|-------|----------------|-------|
| **MultiModalEncoder**     | 19.4  | Embedding vectors | Enhances slot extraction via semantic similarity |
| **ContextEngine**         | 19.3  | Conversation context | Resolves anaphora ("do *that* again") |

### CognitiveCycle Integration

```python
# Inside CognitiveCycle._run_step()
async def _nlp_step(self, raw_input: str) -> None:
    frame = await self._semantic_parser.parse(raw_input)
    await self._blackboard.post("nlp.semantic_frame", frame)
    if frame.confidence_level == IntentConfidence.LOW:
        await self._blackboard.post("nlp.clarification_needed", frame.raw_text)
```

---

## Prometheus Metrics

| # | Metric Name                                  | Type      | Labels           | Description |
|---|----------------------------------------------|-----------|------------------|-------------|
| 1 | `asi_semantic_parser_parse_total`            | Counter   | `intent`, `level`| Total parse() calls by intent and confidence level |
| 2 | `asi_semantic_parser_parse_seconds`          | Histogram | `backend`        | Latency per parse() call |
| 3 | `asi_semantic_parser_fallback_total`         | Counter   | —                | Times the fallback intent was returned |
| 4 | `asi_semantic_parser_slots_extracted`        | Histogram | `slot_type`      | Distribution of slot count per frame |
| 5 | `asi_semantic_parser_patterns_registered`    | Gauge     | —                | Current number of registered patterns |

### PromQL Examples

```promql
# Parse success rate (non-fallback)
1 - (rate(asi_semantic_parser_fallback_total[5m])
     / rate(asi_semantic_parser_parse_total[5m]))

# p99 parse latency
histogram_quantile(0.99, rate(asi_semantic_parser_parse_seconds_bucket[5m]))

# High-confidence parse ratio
rate(asi_semantic_parser_parse_total{level="high"}[5m])
/ rate(asi_semantic_parser_parse_total[5m])
```

### Grafana Alert YAML

```yaml
- alert: SemanticParserHighFallbackRate
  expr: |
    rate(asi_semantic_parser_fallback_total[10m])
    / rate(asi_semantic_parser_parse_total[10m]) > 0.40
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: ">40% of utterances hitting fallback intent"

- alert: SemanticParserLatencySpike
  expr: |
    histogram_quantile(0.99, rate(asi_semantic_parser_parse_seconds_bucket[5m])) > 0.5
  for: 3m
  labels:
    severity: critical
  annotations:
    summary: "p99 parse latency exceeds 500ms"

- alert: SemanticParserNoPatterns
  expr: asi_semantic_parser_patterns_registered == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "No patterns registered — all parses will fallback"
```

---

## mypy Strict Compliance

| Area                     | Technique                                      |
|--------------------------|-------------------------------------------------|
| `Slot.value: Any`        | Accept `Any` for flexibility; callers narrow via `slot_type` |
| `_patterns` SortedList   | `SortedList[tuple[int, str, re.Pattern[str]]]` — fully parameterised |
| `parse()` return         | Always `SemanticFrame` (never `None`)          |
| `get_intents()` return   | `frozenset[str]` — immutable snapshot           |
| `register_pattern()`     | `priority: int` keyword-only, no implicit coercion |

---

## Test Targets (12)

| #  | Test Name                                           | Scope |
|----|-----------------------------------------------------|-------|
| 1  | `test_parse_known_intent_returns_high_confidence`   | Unit — known pattern → HIGH |
| 2  | `test_parse_unknown_text_returns_fallback`           | Unit — no match → fallback intent |
| 3  | `test_parse_extracts_slots_with_correct_types`       | Unit — DATE, NUMBER, ENTITY inferred |
| 4  | `test_parse_batch_returns_correct_count`             | Unit — len(results) == len(inputs) |
| 5  | `test_register_pattern_adds_intent`                 | Unit — get_intents() grows |
| 6  | `test_register_pattern_priority_ordering`            | Unit — higher priority tried first |
| 7  | `test_max_slots_cap_enforced`                       | Unit — frame.slots capped at max_slots |
| 8  | `test_confidence_threshold_triggers_fallback`        | Unit — score below threshold → fallback |
| 9  | `test_null_parser_returns_zero_confidence`           | Unit — NullSemanticParser contract |
| 10 | `test_factory_rule_based_backend`                    | Integration — make_semantic_parser("rule_based") |
| 11 | `test_factory_unknown_backend_raises`                | Integration — ValueError on bad backend |
| 12 | `test_concurrent_parse_and_register_safe`            | Stress — asyncio.gather parse + register_pattern |

### Sample Test Skeletons

```python
@pytest.mark.asyncio
async def test_parse_known_intent_returns_high_confidence():
    parser = make_semantic_parser()
    parser.register_pattern("greet", r"^(hello|hi|hey)\b", priority=10)
    frame = await parser.parse("hello world")
    assert frame.intent == "greet"
    assert frame.confidence_level == IntentConfidence.HIGH
    assert frame.raw_text == "hello world"

@pytest.mark.asyncio
async def test_concurrent_parse_and_register_safe():
    parser = make_semantic_parser()
    parser.register_pattern("ping", r"^ping$", priority=5)

    async def do_parses():
        return [await parser.parse("ping") for _ in range(50)]

    async def do_registers():
        for i in range(50):
            parser.register_pattern(f"dyn_{i}", rf"^dyn_{i}$", priority=1)

    results, _ = await asyncio.gather(do_parses(), do_registers())
    assert all(r.intent == "ping" for r in results)
    assert len(parser.get_intents()) >= 51  # "ping" + 50 dynamic
```

---

## Implementation Order (16 steps)

| Step | Task                                          | File(s) |
|------|-----------------------------------------------|---------|
| 1    | Create `asi/nlp/` package with `__init__.py`  | `asi/nlp/__init__.py` |
| 2    | Define `IntentConfidence` enum                | `asi/nlp/types.py` |
| 3    | Define `SlotType` enum                        | `asi/nlp/types.py` |
| 4    | Define `Slot` frozen dataclass                | `asi/nlp/types.py` |
| 5    | Define `SemanticFrame` frozen dataclass       | `asi/nlp/types.py` |
| 6    | Define `ParserConfig` frozen dataclass        | `asi/nlp/types.py` |
| 7    | Define `SemanticParser` Protocol              | `asi/nlp/protocols.py` |
| 8    | Implement `NullSemanticParser`                | `asi/nlp/null_parser.py` |
| 9    | Implement `RuleBasedSemanticParser.__init__`  | `asi/nlp/rule_parser.py` |
| 10   | Implement `register_pattern()` + `get_intents()` | `asi/nlp/rule_parser.py` |
| 11   | Implement `_tokenize()` + `_match_patterns()` | `asi/nlp/rule_parser.py` |
| 12   | Implement `_extract_slots()` + type inference | `asi/nlp/rule_parser.py` |
| 13   | Implement `_score()` + confidence bucketing   | `asi/nlp/rule_parser.py` |
| 14   | Implement `parse()` → full pipeline          | `asi/nlp/rule_parser.py` |
| 15   | Implement `parse_batch()` via gather          | `asi/nlp/rule_parser.py` |
| 16   | Implement `make_semantic_parser()` factory    | `asi/nlp/factory.py` |

---

## Phase 19 Sub-phase Tracker

| Sub-phase | Component               | Issue | Wiki | Status |
|-----------|-------------------------|-------|------|--------|
| 19.1      | **SemanticParser**      | [#466](https://github.com/web3guru888/asi-build/issues/466) | ✅ | 🟡 Spec'd |
| 19.2      | DialogueManager         | TBD   | —    | ⬜ Planned |
| 19.3      | ContextEngine           | TBD   | —    | ⬜ Planned |
| 19.4      | MultiModalEncoder       | TBD   | —    | ⬜ Planned |
| 19.5      | NLUOrchestrator         | TBD   | —    | ⬜ Planned |

---

*Last updated: 2026-04-13 · ASI:BUILD Phase 19 — Natural-Language Understanding*
