# Phase 19.3 — ResponseGenerator

**Phase 19: Natural-Language Communication & Dialogue**  
Sub-phase 3 of 5 · Issue · Show & Tell · Q&A

---

## Overview

`ResponseGenerator` produces **natural-language responses from structured dialogue state**, converting the semantic output of the dialogue manager into fluent, context-appropriate text. Rather than relying on rigid templates, it uses a **template-free architecture** built from composable sentence planners and surface realisers.

The pipeline takes a `ResponsePlan` (dialogue act + content slots + stylistic constraints) and runs it through two stages:

1. **Sentence Planner** — maps dialogue acts and content slots to ordered sentence fragments (propositions, hedges, connectives).
2. **Surface Realiser** — applies style/tone transformations, synonym substitution, verbosity adjustments, and produces the final natural-language string.

This two-stage separation lets each concern evolve independently: new dialogue acts only touch the planner; new styles or tones only touch the realiser.

---

## Enums

### `ResponseStyle`

Controls the register and formality of generated text.

| Value | Register | Example phrase |
|-------|----------|----------------|
| `FORMAL` | Academic / professional | "The analysis indicates that…" |
| `CASUAL` | Conversational / friendly | "Looks like…" |
| `TECHNICAL` | Precise / jargon-rich | "The O(n log n) amortised complexity ensures…" |
| `CONCISE` | Minimal / telegraphic | "Result: 42. Status: OK." |

```python
class ResponseStyle(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    CONCISE = "concise"
```

### `ResponseTone`

Controls the emotional colouring overlaid on the response style.

| Value | Markers | When to use |
|-------|---------|-------------|
| `NEUTRAL` | No hedges or intensifiers | Default / informational |
| `EMPATHETIC` | "I understand…", "That makes sense…" | Error recovery, user frustration |
| `ASSERTIVE` | "Clearly…", "The evidence shows…" | High-confidence results |
| `ENCOURAGING` | "Great question!", "You're on the right track…" | Onboarding, learning contexts |

```python
class ResponseTone(str, Enum):
    NEUTRAL = "neutral"
    EMPATHETIC = "empathetic"
    ASSERTIVE = "assertive"
    ENCOURAGING = "encouraging"
```

### `Verbosity`

Controls the target length and detail level.

| Value | Token target | Behaviour |
|-------|-------------|-----------|
| `BRIEF` | ≤ 50 tokens | Strip qualifiers, omit examples, one-sentence answers |
| `STANDARD` | 50–200 tokens | Balanced detail with one supporting example |
| `DETAILED` | 200–500 tokens | Full explanation, multiple examples, caveats |

```python
class Verbosity(str, Enum):
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"
```

---

## Data Classes

### `ResponsePlan`

Captures the semantic intent that the generator must realise.

```python
@dataclass(frozen=True)
class ResponsePlan:
    dialogue_act: str              # e.g. "inform", "confirm", "clarify", "apologise"
    content_slots: Mapping[str, Any]  # key-value pairs to verbalise
    style: ResponseStyle           # register
    tone: ResponseTone             # emotional colouring
    verbosity: Verbosity           # target length
    context_turns: tuple[str, ...]  # recent conversation turns for coherence
    priority: float = 0.5         # 0.0 = background, 1.0 = urgent
```

**Design notes**:
- `dialogue_act` uses string tags (not an enum) to allow extension without modifying the core module.
- `content_slots` is `Mapping` (read-only); the generator never mutates the plan.
- `context_turns` is a tuple (hashable) so plans can be cached or deduped.

### `GeneratedResponse`

The output artifact from the generator.

```python
@dataclass(frozen=True)
class GeneratedResponse:
    text: str                        # primary natural-language output
    plan: ResponsePlan               # source plan for traceability
    confidence: float                # 0.0–1.0 generation confidence
    alternatives: tuple[str, ...]    # alternative phrasings (may be empty)
    generation_time_ms: float        # wall-clock generation latency
    token_count: int                 # tokens in primary text
```

**Invariants**:
- `0.0 ≤ confidence ≤ 1.0`
- `len(alternatives) ≤ config.num_alternatives`
- `token_count ≤ config.max_length`

### `GeneratorConfig`

Configures the generator instance.

```python
@dataclass(frozen=True)
class GeneratorConfig:
    default_style: ResponseStyle = ResponseStyle.FORMAL
    default_tone: ResponseTone = ResponseTone.NEUTRAL
    default_verbosity: Verbosity = Verbosity.STANDARD
    max_length: int = 500              # hard token cap
    temperature: float = 0.7           # phrasing diversity (0.0 = deterministic)
    num_alternatives: int = 2          # number of alternative phrasings
    synonym_pool_size: int = 50        # max synonyms per root word loaded
    cache_capacity: int = 256          # LRU plan→response cache slots
    metrics_prefix: str = "asi_response_gen"
```

---

## Protocol

```python
@runtime_checkable
class ResponseGenerator(Protocol):
    async def generate(self, plan: ResponsePlan) -> GeneratedResponse:
        """Generate a response from a pre-built plan."""
        ...

    async def generate_from_state(
        self, state: "DialogueState", **overrides: Any
    ) -> GeneratedResponse:
        """Build a plan from DialogueState, then generate.

        ``overrides`` can set style, tone, verbosity to
        override DialogueState defaults.
        """
        ...

    async def rephrase(
        self, response: GeneratedResponse, *, style: ResponseStyle | None = None,
        tone: ResponseTone | None = None
    ) -> GeneratedResponse:
        """Re-generate with altered style/tone, preserving semantics."""
        ...

    async def get_templates(self) -> Mapping[str, list[str]]:
        """Return the current phrase pool per dialogue act (debugging aid)."""
        ...
```

**Protocol contract**:
- All methods are `async` to allow I/O-bound backends (e.g. LLM calls) in the future.
- `generate_from_state()` creates a `ResponsePlan` internally, then delegates to `generate()`.
- `rephrase()` preserves `dialogue_act` and `content_slots`, only changing surface form.

---

## Implementation: `RuleBasedResponseGenerator`

A deterministic, rule-based implementation with no external LLM dependency. Ideal for testing, offline operation, and low-latency scenarios.

### Architecture

```
ResponsePlan
  │
  ▼
┌──────────────────┐
│  SentencePlanner  │  dialogue_act + slots → ordered fragments
│  ┌──────────────┐ │
│  │ act_handlers  │ │  dict[str, Callable] — one per dialogue_act
│  └──────────────┘ │
└──────────────────┘
  │  list[str]  (fragments)
  ▼
┌──────────────────┐
│  SurfaceRealiser  │  fragments → styled, toned natural-language text
│  ┌──────────────┐ │
│  │ synonym_pool  │ │  dict[str, list[str]] — loaded from JSON
│  │ style_rules   │ │  style → transformation pipeline
│  │ tone_markers   │ │  tone → prefix/suffix injectors
│  └──────────────┘ │
└──────────────────┘
  │  str
  ▼
GeneratedResponse
```

### Sentence Planner

Maps each `dialogue_act` to an ordered list of sentence fragments:

| Dialogue act | Fragment pattern | Example fragments |
|--------------|-----------------|-------------------|
| `inform` | `[hedge?, subject, predicate, evidence?]` | `["The result", "is 42", "based on 3 sources"]` |
| `confirm` | `[affirmation, restatement]` | `["Yes", "the file has been saved"]` |
| `clarify` | `[acknowledgement, disambiguation, question?]` | `["I see", "you mean the prod cluster", "correct?"]` |
| `apologise` | `[apology, explanation, remedy]` | `["Sorry about that", "the timeout was unexpected", "retrying now"]` |
| `suggest` | `[proposal, rationale, qualifier?]` | `["You might try", "increasing the batch size", "if memory allows"]` |

- Unknown dialogue acts fall back to a generic `[subject, predicate]` pattern.
- Content slots are interpolated into fragment templates via `{slot_name}` placeholders.

### Surface Realiser

Applies transformations in a fixed pipeline order:

1. **Join fragments** — concatenate with appropriate punctuation.
2. **Style adjustment** — FORMAL uppercases sentence starts and adds discourse markers ("Furthermore", "In addition"); CASUAL contracts ("it's", "you're") and drops hedges; TECHNICAL injects jargon markers; CONCISE strips everything to bare propositions.
3. **Tone injection** — EMPATHETIC prepends softeners ("I understand…"); ASSERTIVE inserts confidence markers ("Clearly…", "Without doubt…"); ENCOURAGING wraps with positive framing.
4. **Verbosity filtering** — BRIEF: remove qualifier fragments, cap at 50 tokens. STANDARD: keep one example. DETAILED: expand with all examples and caveats.
5. **Synonym substitution** — when `temperature > 0`, sample from synonym pool to introduce phrasing variety. Higher temperature → more adventurous substitutions.

### Alternatives Generation

When `num_alternatives > 0`, the generator produces N additional phrasings by:
1. Sampling different synonym paths for each substitution point.
2. Reordering optional fragments (e.g. moving evidence before predicate).
3. Scoring each alternative by a simple fluency heuristic (bigram frequency).

### Thread Safety

- `asyncio.Lock` guards the synonym pool and LRU cache during concurrent generation.
- The plan→response LRU cache (`cache_capacity` slots) avoids redundant work for repeated plans.

```python
class RuleBasedResponseGenerator:
    def __init__(self, config: GeneratorConfig) -> None:
        self._config = config
        self._lock = asyncio.Lock()
        self._cache: OrderedDict[int, GeneratedResponse] = OrderedDict()
        self._synonym_pool: dict[str, list[str]] = _load_synonyms(config.synonym_pool_size)
        self._planner = SentencePlanner()
        self._realiser = SurfaceRealiser(
            synonyms=self._synonym_pool,
            temperature=config.temperature,
        )
        # Prometheus
        self._gen_counter = Counter(f"{config.metrics_prefix}_generated_total", ...)
        self._gen_duration = Histogram(f"{config.metrics_prefix}_generation_seconds", ...)
        self._token_hist = Histogram(f"{config.metrics_prefix}_token_count", ...)
        self._cache_hits = Counter(f"{config.metrics_prefix}_cache_hits_total", ...)
        self._alt_counter = Counter(f"{config.metrics_prefix}_alternatives_total", ...)

    async def generate(self, plan: ResponsePlan) -> GeneratedResponse:
        async with self._lock:
            cache_key = hash(plan)
            if cache_key in self._cache:
                self._cache_hits.inc()
                return self._cache[cache_key]

        start = time.monotonic()
        fragments = self._planner.plan(plan.dialogue_act, plan.content_slots)
        text = self._realiser.realise(
            fragments, style=plan.style, tone=plan.tone, verbosity=plan.verbosity,
        )
        alternatives = tuple(
            self._realiser.realise_variant(fragments, plan.style, plan.tone, plan.verbosity)
            for _ in range(self._config.num_alternatives)
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        token_count = _count_tokens(text)

        result = GeneratedResponse(
            text=text, plan=plan, confidence=_fluency_score(text),
            alternatives=alternatives, generation_time_ms=elapsed_ms,
            token_count=min(token_count, self._config.max_length),
        )

        async with self._lock:
            self._cache[cache_key] = result
            if len(self._cache) > self._config.cache_capacity:
                self._cache.popitem(last=False)

        self._gen_counter.inc()
        self._gen_duration.observe(elapsed_ms / 1000)
        self._token_hist.observe(token_count)
        self._alt_counter.inc(len(alternatives))
        return result

    async def generate_from_state(self, state: "DialogueState", **overrides) -> GeneratedResponse:
        plan = _state_to_plan(state, self._config, **overrides)
        return await self.generate(plan)

    async def rephrase(self, response: GeneratedResponse, *,
                       style: ResponseStyle | None = None,
                       tone: ResponseTone | None = None) -> GeneratedResponse:
        new_plan = replace(response.plan,
                           style=style or response.plan.style,
                           tone=tone or response.plan.tone)
        return await self.generate(new_plan)

    async def get_templates(self) -> Mapping[str, list[str]]:
        return self._planner.get_all_templates()
```

---

## Implementation: `NullResponseGenerator`

No-op implementation for testing and pipeline stubs.

```python
class NullResponseGenerator:
    async def generate(self, plan: ResponsePlan) -> GeneratedResponse:
        return GeneratedResponse(
            text="", plan=plan, confidence=0.0, alternatives=(),
            generation_time_ms=0.0, token_count=0,
        )

    async def generate_from_state(self, state, **kw) -> GeneratedResponse:
        return await self.generate(_empty_plan())

    async def rephrase(self, response, **kw) -> GeneratedResponse:
        return response

    async def get_templates(self) -> Mapping[str, list[str]]:
        return {}
```

---

## Factory

```python
def make_response_generator(
    config: GeneratorConfig | None = None,
) -> ResponseGenerator:
    cfg = config or GeneratorConfig()
    return RuleBasedResponseGenerator(cfg)
```

---

## Data Flow

```
                          ┌─────────────────┐
  DialogueState ─────────▶│  _state_to_plan  │
  (from DialogueManager   │  (build plan)    │
   19.2)                  └────────┬─────────┘
                                   │ ResponsePlan
                                   ▼
                          ┌─────────────────┐
                          │ SentencePlanner  │
                          │ act → fragments  │
                          └────────┬─────────┘
                                   │ list[str]
                                   ▼
                          ┌─────────────────┐
                          │ SurfaceRealiser  │
                          │ style + tone +   │
                          │ verbosity xform  │
                          └────────┬─────────┘
                                   │ str
                                   ▼
                          ┌─────────────────┐
                          │GeneratedResponse │──────▶ CommunicationOrchestrator 19.5
                          │ text + alts +    │──────▶ ExplainAPI 8.3
                          │ confidence       │
                          └─────────────────┘
```

---

## Integration Map

| Direction | Component | Phase | Interface |
|-----------|-----------|-------|-----------|
| ← input | `DialogueManager` | 19.2 | `generate_from_state(state)` receives `DialogueState` |
| ← input | `IntentClassifier` | 19.1 | Indirect — intent feeds `DialogueState.current_intent` |
| → output | `CommunicationOrchestrator` | 19.5 | Orchestrator calls `generate()` or `generate_from_state()` |
| → output | `ExplainAPI` | 8.3 | Explanation strings formatted via `generate(plan)` with `TECHNICAL` style |
| ↔ peer | `SentimentAnalyser` | 19.4 | Sentiment score may override `tone` in `generate_from_state()` overrides |
| ↔ config | `AlignmentDashboard` | 11.5 | Style/tone defaults can be tuned via alignment policies |

---

## Prometheus Metrics

| # | Metric | Type | Labels | Description |
|---|--------|------|--------|-------------|
| 1 | `asi_response_gen_generated_total` | Counter | `dialogue_act`, `style` | Total responses generated |
| 2 | `asi_response_gen_generation_seconds` | Histogram | `dialogue_act` | Time to generate a response |
| 3 | `asi_response_gen_token_count` | Histogram | `verbosity` | Token count distribution |
| 4 | `asi_response_gen_cache_hits_total` | Counter | — | Plan→response cache hits |
| 5 | `asi_response_gen_alternatives_total` | Counter | `style` | Alternative phrasings produced |

### PromQL Examples

```promql
# Generation rate per dialogue act
sum by (dialogue_act) (rate(asi_response_gen_generated_total[5m]))

# p99 generation latency
histogram_quantile(0.99, rate(asi_response_gen_generation_seconds_bucket[5m]))

# Average token count by verbosity
sum by (verbosity) (rate(asi_response_gen_token_count_sum[5m]))
/ sum by (verbosity) (rate(asi_response_gen_token_count_count[5m]))

# Cache hit ratio
rate(asi_response_gen_cache_hits_total[5m])
/ rate(asi_response_gen_generated_total[5m])
```

### Grafana Alerts

```yaml
# Slow generation (p99 > 200ms)
- alert: ResponseGenSlowGeneration
  expr: histogram_quantile(0.99, rate(asi_response_gen_generation_seconds_bucket[5m])) > 0.2
  for: 5m
  labels:
    severity: warning

# Token overflow (> max_length)
- alert: ResponseGenTokenOverflow
  expr: histogram_quantile(0.99, rate(asi_response_gen_token_count_bucket[5m])) > 500
  for: 3m
  labels:
    severity: warning

# Zero generation (pipeline stall)
- alert: ResponseGenNoOutput
  expr: rate(asi_response_gen_generated_total[10m]) == 0
  for: 10m
  labels:
    severity: critical
```

---

## Mypy Narrowing Table

| Variable | Declared type | Narrowed to | How |
|----------|---------------|-------------|-----|
| `plan.content_slots` | `Mapping[str, Any]` | `dict[str, str]` | cast in `_interpolate_slots` |
| `response.alternatives` | `tuple[str, ...]` | same | frozen dataclass |
| `config` | `GeneratorConfig \| None` | `GeneratorConfig` | `cfg = config or GeneratorConfig()` |
| `style` | `ResponseStyle \| None` | `ResponseStyle` | `style or response.plan.style` |
| `cache_entry` | `GeneratedResponse \| None` | `GeneratedResponse` | `if cache_key in self._cache` |

---

## Test Targets (12)

1. `test_generate_inform_produces_text`
2. `test_generate_confirm_includes_affirmation`
3. `test_style_formal_capitalises_and_hedges`
4. `test_style_casual_contracts_and_drops_hedges`
5. `test_style_concise_strips_to_minimum`
6. `test_tone_empathetic_prepends_softener`
7. `test_tone_assertive_inserts_confidence_marker`
8. `test_verbosity_brief_under_50_tokens`
9. `test_verbosity_detailed_includes_examples`
10. `test_alternatives_count_matches_config`
11. `test_cache_hit_returns_same_response`
12. `test_null_generator_returns_empty`

### Skeletons

```python
@pytest.mark.asyncio
async def test_generate_inform_produces_text():
    gen = make_response_generator()
    plan = ResponsePlan(
        dialogue_act="inform",
        content_slots={"subject": "memory usage", "value": "42%"},
        style=ResponseStyle.FORMAL,
        tone=ResponseTone.NEUTRAL,
        verbosity=Verbosity.STANDARD,
        context_turns=(),
    )
    result = await gen.generate(plan)
    assert len(result.text) > 0
    assert result.token_count > 0
    assert result.confidence > 0.0

@pytest.mark.asyncio
async def test_cache_hit_returns_same_response():
    gen = make_response_generator(GeneratorConfig(temperature=0.0))
    plan = ResponsePlan(
        dialogue_act="confirm",
        content_slots={"action": "saved"},
        style=ResponseStyle.FORMAL,
        tone=ResponseTone.NEUTRAL,
        verbosity=Verbosity.BRIEF,
        context_turns=(),
    )
    r1 = await gen.generate(plan)
    r2 = await gen.generate(plan)
    assert r1.text == r2.text
```

---

## Implementation Order (14 steps)

1. Define `ResponseStyle`, `ResponseTone`, `Verbosity` enums in `enums.py`
2. Define `ResponsePlan`, `GeneratedResponse`, `GeneratorConfig` frozen dataclasses
3. Define `ResponseGenerator` Protocol with 4 async methods
4. Implement `SentencePlanner` with act handler registry
5. Add fragment templates for `inform`, `confirm`, `clarify`, `apologise`, `suggest`
6. Implement `SurfaceRealiser` with style transformation pipeline
7. Add tone injection (prefix/suffix markers per `ResponseTone`)
8. Add verbosity filtering (BRIEF strip, STANDARD keep-one, DETAILED expand)
9. Implement synonym pool loader (`_load_synonyms`) from JSON resource
10. Implement `RuleBasedResponseGenerator.__init__` with cache + metrics
11. Implement `generate()` with planner→realiser→cache pipeline
12. Implement `generate_from_state()` and `rephrase()` convenience methods
13. Implement `NullResponseGenerator` + `make_response_generator()` factory
14. Wire Prometheus metrics + write all 12 tests

---

## Phase 19 Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 19.1 | IntentClassifier | — | ⏳ |
| 19.2 | DialogueManager | — | ⏳ |
| 19.3 | ResponseGenerator | — | 🟡 open |
| 19.4 | SentimentAnalyser | — | ⏳ next |
| 19.5 | CommunicationOrchestrator | — | ⏳ upcoming |
