# Phase 14.1 — CodeSynthesiser

**Phase**: 14 (Autonomous Code Synthesis) · **Sub-phase**: 14.1  
**Issue**: [#385](https://github.com/web3guru888/asi-build/issues/385)  
**Discussions**: [#386 Show & Tell](https://github.com/web3guru888/asi-build/discussions/386) · [#387 Q&A](https://github.com/web3guru888/asi-build/discussions/387)

---

## Overview

`CodeSynthesiser` is the entry point for Phase 14 (Autonomous Code Synthesis). It accepts a typed Python interface (function signature + docstring) and produces one or more candidate implementations using an OpenAI-compatible LLM backend, with support for iterative self-refinement.

Results are passed downstream to `SandboxRunner` (14.2) for isolated execution and `TestHarness` (14.3) for pytest validation, then scored by `PatchSelector` (14.4) and audited by `SynthesisAudit` (14.5).

---

## Data Flow

```
CognitiveCycle
    │
    └─► _synthesis_step(goal_id, interface)
              │
              ▼
         CodeSynthesiser.synthesise(SynthesisRequest)
              │
         ┌────┴────────────────────────────────┐
         │                                      │
    strategy=GREEDY/BEAM/SAMPLE_TOP_K    strategy=SELF_REFINE
         │                                      │
    _call_llm(prompt)              for round in max_refine_rounds:
         │                              _call_llm(critique_prompt)
         │                              if critique == "OK": break
         │                              _call_llm(refine_prompt)
         │                                      │
         └──────────────────┬───────────────────┘
                            ▼
                    SynthesisResult
                (code, tokens_used, latency_ms, score=0.0)
                            │
                            ▼
                    → SandboxRunner (14.2)
```

---

## Enumerations

```python
from enum import Enum

class SynthesisStrategy(str, Enum):
    GREEDY       = "greedy"        # single best token at each step
    BEAM         = "beam"          # beam search (n_beams=4 candidates)
    SAMPLE_TOP_K = "sample_top_k"  # stochastic top-k sampling
    SELF_REFINE  = "self_refine"   # iterative critique + redraft loop
```

---

## Frozen Dataclasses

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class SynthesisRequest:
    interface: str        # full typed function signature + docstring
    goal_id: str          # GoalRegistry ID driving this synthesis
    strategy: SynthesisStrategy = SynthesisStrategy.GREEDY
    max_tokens: int = 512
    temperature: float = 0.2
    n_candidates: int = 1
    examples: tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class SynthesisResult:
    code: str
    strategy: SynthesisStrategy
    tokens_used: int
    latency_ms: float
    score: float          # placeholder — set by PatchSelector (14.4)
    refine_rounds: int = 0

@dataclass(frozen=True)
class SynthesiserConfig:
    llm_base_url: str = "http://localhost:8080"
    llm_model: str = "gpt-4o-mini"
    max_refine_rounds: int = 3
    refine_threshold: float = 0.7   # stop refining if score >= threshold
    timeout_s: float = 30.0
    enabled: bool = True
```

---

## Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class CodeSynthesiser(Protocol):
    async def synthesise(self, request: SynthesisRequest) -> SynthesisResult: ...
    async def refine(
        self,
        result: SynthesisResult,
        feedback: str,
        request: SynthesisRequest,
    ) -> SynthesisResult: ...
    async def batch_synthesise(
        self, requests: list[SynthesisRequest]
    ) -> list[SynthesisResult]: ...
    async def stats(self) -> dict[str, float]: ...
    async def reset(self) -> None: ...
```

---

## InMemoryCodeSynthesiser

### Constructor

```python
class InMemoryCodeSynthesiser:
    def __init__(self, config: SynthesiserConfig | None = None) -> None:
        self._cfg = config or SynthesiserConfig()
        self._lock = asyncio.Lock()
        self._history: deque[SynthesisResult] = deque(maxlen=1000)
        self._total_requests = 0
        self._total_tokens = 0
        self._total_refine_rounds = 0
```

### Prompt Construction

```python
def _build_prompt(self, request: SynthesisRequest) -> str:
    parts = ["Implement the following Python function exactly as specified:", ""]
    parts.append("```python")
    parts.append(request.interface)
    parts.append("```")
    if request.examples:
        parts += ["", "## Examples", ""]
        for ex in request.examples:
            parts.append(ex)
    parts += ["", "Return ONLY the function body (no markdown wrapper)."]
    return "\n".join(parts)
```

The `Return ONLY the function body` instruction prevents the LLM from wrapping output in markdown or re-including the function signature.

### Self-Refine Loop

```python
async def _self_refine(self, code, request, tokens_so_far):
    rounds = 0
    total_tokens = tokens_so_far
    for _ in range(self._cfg.max_refine_rounds):  # default: 3
        critique_prompt = (
            f"Critique this implementation of:\n```python\n{request.interface}\n```\n"
            f"Implementation:\n```python\n{code}\n```\n"
            "List specific issues. If none, reply exactly 'OK'."
        )
        critique, tok = await self._call_llm(critique_prompt, GREEDY, 256, 0.1)
        total_tokens += tok
        if critique.strip().upper() == "OK":
            break  # early exit when LLM is satisfied
        refine_prompt = self._build_refine_prompt(code, critique, request.interface)
        code, tok = await self._call_llm(refine_prompt, GREEDY, request.max_tokens, 0.2)
        total_tokens += tok
        rounds += 1
    return code, total_tokens, rounds
```

### synthesise() Method

```python
async def synthesise(self, request: SynthesisRequest) -> SynthesisResult:
    if not self._cfg.enabled:
        return SynthesisResult(code="pass  # synthesis disabled",
                               strategy=request.strategy,
                               tokens_used=0, latency_ms=0.0, score=0.0)
    t0 = time.monotonic()
    prompt = self._build_prompt(request)
    code, tokens = await self._call_llm(
        prompt, request.strategy, request.max_tokens, request.temperature
    )
    refine_rounds = 0
    if request.strategy == SynthesisStrategy.SELF_REFINE:
        code, tokens, refine_rounds = await self._self_refine(code, request, tokens)
    latency_ms = (time.monotonic() - t0) * 1000
    result = SynthesisResult(code=code, strategy=request.strategy,
                             tokens_used=tokens, latency_ms=latency_ms,
                             score=0.0, refine_rounds=refine_rounds)
    async with self._lock:
        self._history.append(result)
        self._total_requests += 1
        self._total_tokens += tokens
        self._total_refine_rounds += refine_rounds
    return result
```

### batch_synthesise() — Parallel Dispatch

```python
async def batch_synthesise(self, requests: list[SynthesisRequest]) -> list[SynthesisResult]:
    return list(await asyncio.gather(*[self.synthesise(r) for r in requests]))
```

All requests are dispatched concurrently; the lock is only held for stats updates.

### Factory

```python
def make_code_synthesiser(config: SynthesiserConfig | None = None) -> CodeSynthesiser:
    return InMemoryCodeSynthesiser(config)
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    def __init__(self, ..., synthesiser: CodeSynthesiser | None = None) -> None:
        ...
        self._synthesiser = synthesiser

    async def _synthesis_step(self, goal_id: str, interface: str) -> SynthesisResult | None:
        """Called when a goal requires code generation."""
        if self._synthesiser is None:
            return None
        request = SynthesisRequest(
            interface=interface,
            goal_id=goal_id,
            strategy=SynthesisStrategy.SELF_REFINE,
        )
        return await self._synthesiser.synthesise(request)
```

Pass `synthesiser=None` for zero-overhead no-op mode.

---

## SynthesisStrategy Selection Guide

| Scenario | Strategy | Reason |
|----------|----------|--------|
| Simple 1–3 line utility | `GREEDY` | Minimal token cost |
| Recursive / stateful logic | `SELF_REFINE` | LLM self-critique catches edge cases |
| Exploratory synthesis | `SAMPLE_TOP_K` | Stochastic variety |
| Need top-N candidates | `BEAM` | Forces LLM to sample n=4 completions |

---

## Supported LLM Backends (OpenAI-compatible)

| Backend | llm_base_url | llm_model |
|---------|-------------|----------|
| OpenAI | `https://api.openai.com` | `gpt-4o-mini` |
| Ollama (local) | `http://ollama:11434` | `codellama:13b` |
| vLLM | `http://vllm:8000` | `deepseek-coder-6.7b` |
| LM Studio | `http://localhost:1234` | any GGUF |

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_synthesiser_requests_total` | Counter | `strategy` | Total synthesis requests |
| `asi_synthesiser_tokens_total` | Counter | `strategy` | Total LLM tokens consumed |
| `asi_synthesiser_latency_ms` | Histogram | `strategy` | End-to-end synthesis latency |
| `asi_synthesiser_refine_rounds_total` | Counter | — | Cumulative self-refine iterations |
| `asi_synthesiser_enabled` | Gauge | — | 1 if synthesis is enabled |

### PromQL Examples

```promql
# Token consumption rate (tokens/min)
rate(asi_synthesiser_tokens_total[5m]) * 60

# p99 synthesis latency
histogram_quantile(0.99, rate(asi_synthesiser_latency_ms_bucket[5m]))

# Self-refine rounds per minute
rate(asi_synthesiser_refine_rounds_total[5m]) * 60
```

### Grafana Alert

```yaml
- alert: SynthesiserHighTokenRate
  expr: rate(asi_synthesiser_tokens_total[5m]) > 500
  for: 2m
  labels: { severity: warning }
  annotations:
    summary: "CodeSynthesiser consuming >500 tok/min — check SELF_REFINE loop"
```

---

## mypy Table

| Check | Expected |
|-------|----------|
| `synthesise` return type | `SynthesisResult` |
| `batch_synthesise` return type | `list[SynthesisResult]` |
| `SynthesisRequest.examples` | `tuple[str, ...]` |
| `SynthesisStrategy` enum exhaustiveness | no unhandled branches |
| Protocol satisfaction | `isinstance(InMemoryCodeSynthesiser(), CodeSynthesiser)` is `True` |

---

## Test Targets (12)

| # | Test | What it validates |
|---|------|------------------|
| 1 | `test_synthesise_greedy_returns_result` | mock LLM returns code, `result.code` is non-empty |
| 2 | `test_synthesise_self_refine_loops` | 3 critique rounds, `refine_rounds == 3` |
| 3 | `test_synthesise_self_refine_stops_on_ok` | critique returns 'OK', `refine_rounds == 0` |
| 4 | `test_synthesise_disabled_returns_pass` | `enabled=False`, code == `'pass  # synthesis disabled'` |
| 5 | `test_batch_synthesise_parallel` | `asyncio.gather`, all results non-empty |
| 6 | `test_refine_increments_rounds` | `refine()` increments `refine_rounds` by 1 |
| 7 | `test_stats_accumulate` | `total_requests`, `total_tokens` increment correctly |
| 8 | `test_reset_clears_stats` | `reset()` zeros all counters |
| 9 | `test_build_prompt_includes_interface` | prompt contains interface string |
| 10 | `test_build_prompt_includes_examples` | prompt contains example strings |
| 11 | `test_llm_timeout_raises` | httpx timeout propagates as synthesis error |
| 12 | `test_protocol_satisfied` | `isinstance(InMemoryCodeSynthesiser(), CodeSynthesiser)` is `True` |

---

## Implementation Order (14 steps)

1. `SynthesisStrategy` enum
2. `SynthesisRequest`, `SynthesisResult`, `SynthesiserConfig` frozen dataclasses
3. `CodeSynthesiser` Protocol (`@runtime_checkable`)
4. `InMemoryCodeSynthesiser.__init__` (lock + deque + counters)
5. `_build_prompt()` / `_build_refine_prompt()`
6. `_call_llm()` (httpx, OpenAI-compatible)
7. `_self_refine()` loop
8. `synthesise()` (all 4 strategies)
9. `refine()` public method
10. `batch_synthesise()` (`asyncio.gather`)
11. `stats()` / `reset()`
12. `make_code_synthesiser()` factory
13. `CognitiveCycle._synthesis_step()` integration
14. Prometheus metrics + mypy table + 12 test targets

---

## Phase 14 Roadmap

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| 14.1 | `CodeSynthesiser` | 🟡 This page |
| 14.2 | `SandboxRunner` | ⏳ Next |
| 14.3 | `TestHarness` | ⏳ |
| 14.4 | `PatchSelector` | ⏳ |
| 14.5 | `SynthesisAudit` | ⏳ |

### Phase 14 → Phase 13 Integration

| Phase 14 Component | Phase 13 Dependency |
|--------------------|---------------------|
| `CodeSynthesiser` | `CognitiveCycle` (consumes `WorldModel._model_based_step()` context) |
| `SandboxRunner` | `SurpriseDetector` (anomaly alerts on execution failures) |
| `TestHarness` | `WorldModel` (can simulate test outcomes before running) |
| `PatchSelector` | `ValueLearner` (11.3), `CuriosityModule` (13.3) bonus |
| `SynthesisAudit` | `AlignmentMonitor` (11.2) provenance log |

---

*Wiki page 118 · Phase 14.1 · 2026-04-13*
