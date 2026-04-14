# Phase 14.4 — PatchSelector

**Component**: `asi/synthesis/patch_selector.py`  
**Layer**: Code-Synthesis Pipeline (Phase 14)  
**Depends on**: `TestHarness` (Phase 14.3), `SandboxRunner` (Phase 14.2), `CodeSynthesiser` (Phase 14.1)  
**Feeds into**: `SynthesisAudit` (Phase 14.5)  
**Issue**: [#394](https://github.com/web3guru888/asi-build/issues/394)  
**Show & Tell**: [Discussion #395](https://github.com/web3guru888/asi-build/discussions/395)  
**Q&A**: [Discussion #396](https://github.com/web3guru888/asi-build/discussions/396)

---

## Overview

`PatchSelector` is the **decision engine** of the synthesis pipeline. After `TestHarness` evaluates multiple synthesized code patches, `PatchSelector` receives a ranked list of `(SynthesisResult, HarnessStats)` pairs and selects the **best candidate patch** to commit or escalate for review.

Selection criteria are pluggable via a `SelectionStrategy` enum, allowing the pipeline to optimize for pass rate, coverage, latency, or a weighted composite score.

---

## Data Flow

```
CognitiveCycle._synthesis_step()
       │
       ├─ CodeSynthesiser.batch_synthesise([req]*N)  →  [SynthesisResult, ...]
       │
       ├─ for each SynthesisResult:
       │      TestHarness.run_suite(suite)           →  HarnessStats
       │
       ├─ PatchSelector.select([(sr, hs), ...], cfg) →  SelectionResult
       │            │
       │   ┌────────┴──────────────────────────────────┐
       │   │  eligibility filter (pass_rate ≥ threshold) │
       │   │  scoring by SelectionStrategy              │
       │   │  winner = max(eligible, key=score)         │
       │   └────────────────────────────────────────────┘
       │
       └─ winner.synthesis_result  OR  None → ReplanningEngine
```

---

## `SelectionStrategy` Enum

| Value | Optimizes | Best For |
|---|---|---|
| `HIGHEST_PASS_RATE` | max `pass_rate` | safety-critical code |
| `LOWEST_LATENCY` | min `mean_duration_ms` | real-time systems |
| `COMPOSITE_SCORE` | weighted blend (default) | general use |
| `FIRST_PASSING` | first above threshold | fast CI pipelines |

---

## Frozen Dataclasses

```python
@dataclass(frozen=True)
class PatchCandidate:
    synthesis_result: SynthesisResult        # from CodeSynthesiser
    harness_stats: HarnessStats              # from TestHarness
    composite_score: float                   # computed by PatchSelector
    selected_at: datetime

@dataclass(frozen=True)
class SelectionResult:
    winner: PatchCandidate | None            # None → no candidate passed threshold
    all_candidates: tuple[PatchCandidate, ...]
    strategy_used: SelectionStrategy
    selection_duration_ms: float

@dataclass(frozen=True)
class SelectorConfig:
    strategy: SelectionStrategy = SelectionStrategy.COMPOSITE_SCORE
    pass_rate_threshold: float = 0.80        # minimum pass_rate to be eligible
    weight_pass_rate: float = 0.70           # composite weight
    weight_speed: float = 0.30              # composite weight (must sum to 1.0)
    max_latency_ms: float = 5_000.0         # normalisation ceiling

    def __post_init__(self) -> None:
        total = self.weight_pass_rate + self.weight_speed
        if not (0.999 < total < 1.001):
            raise ValueError(f"Weights must sum to 1.0, got {total}")
```

---

## `PatchSelector` Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class PatchSelector(Protocol):
    """Select the best patch candidate from evaluated results."""

    async def select(
        self,
        candidates: Sequence[tuple[SynthesisResult, HarnessStats]],
        config: SelectorConfig,
    ) -> SelectionResult: ...

    def stats(self) -> dict[str, int | float]: ...
    def reset(self) -> None: ...
```

---

## `RankedPatchSelector` — Reference Implementation

```python
class RankedPatchSelector:
    """Score and rank patch candidates; return SelectionResult."""

    def __init__(self) -> None:
        self._selections: int = 0
        self._no_winner: int = 0
        self._total_duration_ms: float = 0.0

    def _composite_score(self, hs: HarnessStats, cfg: SelectorConfig) -> float:
        norm_latency = min(hs.mean_duration_ms, cfg.max_latency_ms) / cfg.max_latency_ms
        return cfg.weight_pass_rate * hs.pass_rate + cfg.weight_speed * (1.0 - norm_latency)

    def _score_candidate(
        self, sr: SynthesisResult, hs: HarnessStats, cfg: SelectorConfig
    ) -> PatchCandidate:
        match cfg.strategy:
            case SelectionStrategy.HIGHEST_PASS_RATE:
                score = hs.pass_rate
            case SelectionStrategy.LOWEST_LATENCY:
                score = 1.0 - min(hs.mean_duration_ms, cfg.max_latency_ms) / cfg.max_latency_ms
            case SelectionStrategy.COMPOSITE_SCORE:
                score = self._composite_score(hs, cfg)
            case SelectionStrategy.FIRST_PASSING:
                score = 1.0 if hs.pass_rate >= cfg.pass_rate_threshold else 0.0
        return PatchCandidate(
            synthesis_result=sr,
            harness_stats=hs,
            composite_score=score,
            selected_at=datetime.now(tz=timezone.utc),
        )

    async def select(
        self,
        candidates: Sequence[tuple[SynthesisResult, HarnessStats]],
        config: SelectorConfig,
    ) -> SelectionResult:
        t0 = asyncio.get_event_loop().time()
        scored = [self._score_candidate(sr, hs, config) for sr, hs in candidates]
        eligible = [c for c in scored if c.harness_stats.pass_rate >= config.pass_rate_threshold]

        if config.strategy == SelectionStrategy.FIRST_PASSING:
            winner = next(
                (c for c in scored if c.harness_stats.pass_rate >= config.pass_rate_threshold),
                None,
            )
        else:
            winner = max(eligible, key=lambda c: c.composite_score) if eligible else None

        duration_ms = (asyncio.get_event_loop().time() - t0) * 1000
        self._selections += 1
        if winner is None:
            self._no_winner += 1
        self._total_duration_ms += duration_ms

        return SelectionResult(
            winner=winner,
            all_candidates=tuple(scored),
            strategy_used=config.strategy,
            selection_duration_ms=duration_ms,
        )

    def stats(self) -> dict[str, int | float]:
        return {
            "selections_total": self._selections,
            "no_winner_total": self._no_winner,
            "mean_duration_ms": self._total_duration_ms / max(self._selections, 1),
        }

    def reset(self) -> None:
        self._selections = 0
        self._no_winner = 0
        self._total_duration_ms = 0.0


def make_patch_selector() -> PatchSelector:
    return RankedPatchSelector()
```

---

## CognitiveCycle Integration

```python
# asi/cognitive_cycle.py  (updated _synthesis_step)

async def _synthesis_step(
    self,
    task: str,
    synthesiser: CodeSynthesiser,
    sandbox: SandboxRunner,
    harness: TestHarness,
    selector: PatchSelector,
    selector_cfg: SelectorConfig,
) -> SynthesisResult | None:
    candidates: list[tuple[SynthesisResult, HarnessStats]] = []
    for result in await synthesiser.batch_synthesise([SynthesisRequest(task=task)] * 3):
        suite = [TestCase(name=f"tc_{i}", code=result.code) for i in range(5)]
        stats = await harness.run_suite(suite)
        candidates.append((result, stats))

    selection = await selector.select(candidates, selector_cfg)
    if selection.winner is None:
        await self._replanning_engine.replan(task)
        return None
    return selection.winner.synthesis_result
```

---

## Strategy Selection Guide

| Scenario | Recommended Strategy | Threshold |
|---|---|---|
| Safety-critical / correctness-first | `HIGHEST_PASS_RATE` | 0.95 |
| Real-time / latency-sensitive | `LOWEST_LATENCY` | 0.80 |
| General balanced pipeline | `COMPOSITE_SCORE` | 0.80 |
| Fast CI with early exit | `FIRST_PASSING` | 0.70 |

---

## Composite Score Formula

```
score = weight_pass_rate × pass_rate
      + weight_speed × (1 - min(mean_ms, max_latency_ms) / max_latency_ms)

Default: 0.70 × pass_rate + 0.30 × speed_factor
```

Example — 3 candidates with `max_latency_ms=5000`:

| Candidate | pass_rate | mean_ms | norm_latency | composite |
|---|---|---|---|---|
| A | 0.95 | 800 | 0.160 | 0.665 + 0.252 = **0.917** |
| B | 0.80 | 200 | 0.040 | 0.560 + 0.288 = **0.848** |
| C | 0.70 | 50  | 0.010 | ineligible (< 0.80 threshold) |

→ Candidate **A** wins.

---

## Prometheus Metrics

| Metric | Type | Description |
|---|---|---|
| `asi_patch_selections_total` | Counter | Total selection rounds |
| `asi_patch_no_winner_total` | Counter | Rounds with no eligible candidate |
| `asi_patch_winner_score` | Histogram | Winning candidate composite score |
| `asi_patch_candidates_evaluated` | Histogram | Number of candidates per round |
| `asi_patch_selection_duration_ms` | Histogram | Time to select (ms) |

### PromQL

```promql
# No-winner rate (alert if > 20%)
rate(asi_patch_no_winner_total[5m]) / rate(asi_patch_selections_total[5m]) > 0.20

# P99 selection latency
histogram_quantile(0.99, rate(asi_patch_selection_duration_ms_bucket[5m]))

# Mean winner score trend
rate(asi_patch_winner_score_sum[5m]) / rate(asi_patch_winner_score_count[5m])
```

### Grafana Alert

```yaml
groups:
  - name: asi_patch_selector
    rules:
      - alert: PatchSelectorHighNoWinnerRate
        expr: >
          rate(asi_patch_no_winner_total[5m])
          / rate(asi_patch_selections_total[5m]) > 0.20
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PatchSelector no-winner rate > 20% — synthesiser quality degraded"
      - alert: PatchSelectorHighLatency
        expr: histogram_quantile(0.99, rate(asi_patch_selection_duration_ms_bucket[5m])) > 100
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "PatchSelector P99 latency > 100ms"
```

---

## mypy Compliance

| Symbol | Flag |
|---|---|
| `PatchSelector` Protocol | `--strict` ok |
| `RankedPatchSelector` | `--disallow-untyped-defs` ok |
| `SelectorConfig.__post_init__` | weight validation |
| `SelectionResult.winner` | `PatchCandidate \| None` — assert before use |

---

## Test Targets (12)

1. `test_highest_pass_rate_strategy` — winner has max pass_rate among eligible
2. `test_lowest_latency_strategy` — winner has min mean_duration_ms
3. `test_composite_score_strategy` — weighted blend computed correctly
4. `test_first_passing_strategy` — returns first above threshold
5. `test_no_eligible_winner_is_none` — all below threshold → winner None
6. `test_threshold_boundary` — candidate at exactly threshold is eligible
7. `test_empty_candidates` — empty list → winner None
8. `test_all_candidates_in_result` — SelectionResult.all_candidates includes all
9. `test_strategy_used_recorded` — SelectionResult.strategy_used matches config
10. `test_stats_accumulation` — selections_total / no_winner_total tracked
11. `test_reset_clears_stats` — reset() zeros counters
12. `test_cognitive_cycle_injection` — mock selector.select() called with candidates

---

## Implementation Order (14 steps)

1. Create `asi/synthesis/patch_selector.py`
2. Define `SelectionStrategy` enum
3. Implement `PatchCandidate` frozen dataclass
4. Implement `SelectionResult` frozen dataclass
5. Implement `SelectorConfig` frozen dataclass with `__post_init__` weight validation
6. Define `PatchSelector` Protocol (`@runtime_checkable`)
7. Implement `RankedPatchSelector._score_candidate()` with strategy dispatch
8. Implement `RankedPatchSelector._composite_score()` helper
9. Implement `RankedPatchSelector.select()` with eligibility filter
10. Implement `RankedPatchSelector.stats()` and `reset()`
11. Implement `make_patch_selector()` factory
12. Register Prometheus metrics (5 instruments)
13. Update `CognitiveCycle._synthesis_step()` with selector injection
14. Write 12 unit tests

---

## Phase 14 Roadmap

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 14.1 | CodeSynthesiser | [#385](https://github.com/web3guru888/asi-build/issues/385) | 🟡 Spec filed |
| 14.2 | SandboxRunner | [#388](https://github.com/web3guru888/asi-build/issues/388) | 🟡 Spec filed |
| 14.3 | TestHarness | [#391](https://github.com/web3guru888/asi-build/issues/391) | 🟡 Spec filed |
| 14.4 | PatchSelector | [#394](https://github.com/web3guru888/asi-build/issues/394) | 🟡 Spec filed |
| 14.5 | SynthesisAudit | — | ⏳ Next |

---

## Phase 14 Integration Table

| Component | Produces | Consumed By |
|---|---|---|
| `CodeSynthesiser` | `SynthesisResult` | `SandboxRunner`, `TestHarness`, `PatchSelector` |
| `SandboxRunner` | `ExecutionResult` | `TestHarness` |
| `TestHarness` | `HarnessStats` | `PatchSelector` |
| `PatchSelector` | `SelectionResult` | `CognitiveCycle`, `SynthesisAudit` |
| `SynthesisAudit` | audit log | monitoring / human review |
