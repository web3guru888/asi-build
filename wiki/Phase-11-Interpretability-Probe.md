# Phase 11.4 — InterpretabilityProbe

**Phase**: 11 — Safety & Alignment  
**Depends on**: [Phase 11.1 SafetyFilter](Phase-11-Safety-Filter), [Phase 11.2 AlignmentMonitor](Phase-11-Alignment-Monitor), [Phase 11.3 ValueLearner](Phase-11-Value-Learner)  
**Issue**: [#346](https://github.com/web3guru888/asi-build/issues/346)  
**Discussions**: [#347 Show & Tell](https://github.com/web3guru888/asi-build/discussions/347) · [#348 Q&A](https://github.com/web3guru888/asi-build/discussions/348)

---

## Motivation

`SafetyFilter` blocks or allows goals based on constitutional rules. `AlignmentMonitor` scores behavioral health across 5 dimensions. `ValueLearner` fine-tunes reward weights from human feedback. But none of these components answer: **why did the system make this decision?**

`InterpretabilityProbe` provides post-hoc explanation of alignment decisions using feature attribution — identifying which input features most influenced a `SafetyFilter` verdict, `AlignmentMonitor` score, or `ValueLearner` weight update. It makes the safety layer *auditable* and *understandable*.

---

## Core abstractions

### `AttributionMethod` enum

```python
class AttributionMethod(Enum):
    GRADIENT_SHAP    = "gradient_shap"   # SHAP-style gradient × input
    LIME_LOCAL       = "lime_local"      # LIME local linear approximation
    INTEGRATED_GRAD  = "integrated_grad" # integrated gradients (50-step Riemann sum)
    PERMUTATION      = "permutation"     # zero-baseline ablation (default)
```

### `ExplanationTarget` enum

```python
class ExplanationTarget(Enum):
    SAFETY_VERDICT   = "safety_verdict"   # explain SafetyFilter BLOCK/ALLOW
    ALIGNMENT_SCORE  = "alignment_score"  # explain AlignmentMonitor dimension score
    REWARD_WEIGHT    = "reward_weight"    # explain ValueLearner weight update
```

### Frozen dataclasses

```python
@dataclass(frozen=True)
class FeatureAttribution:
    feature_name: str
    attribution_score: float   # signed; positive = pushed toward decision
    relative_importance: float # |score| / sum(|scores|) — [0, 1]

@dataclass(frozen=True)
class ProbeExplanation:
    explanation_id: str                       # UUID
    target: ExplanationTarget
    subject_id: str                           # goal_id / sample_id / entry_id
    method: AttributionMethod
    decision_value: float                     # the value being explained
    attributions: tuple[FeatureAttribution, ...]
    counterfactual: tuple[str, ...] | None    # top-k feature flips to reverse decision
    confidence: float                         # [0, 1] — explanation reliability
    generated_at: float                       # epoch seconds

@dataclass(frozen=True)
class ProbeConfig:
    method: AttributionMethod = AttributionMethod.PERMUTATION
    top_k_features: int = 10
    n_lime_samples: int = 100
    counterfactual_max_flips: int = 3
    cache_ttl_s: float = 300.0
    max_cache_entries: int = 1_000

@dataclass(frozen=True)
class ProbeSnapshot:
    total_explanations: int
    cache_hit_rate: float
    method_distribution: tuple[tuple[str, int], ...]
    target_distribution: tuple[tuple[str, int], ...]
    avg_attribution_compute_ms: float
    snapshot_at: float
```

---

## Feature vector design

### SafetyFilter verdict features (12 dimensions)

| # | Feature | Description |
|---|---------|-------------|
| 0 | `goal_priority` | normalised [0, 1] |
| 1 | `task_count` | log-normalised count |
| 2–5 | `capability_bits` | 4-bit one-hot |
| 6 | `resource_budget_cpu` | declared CPU budget |
| 7 | `resource_budget_mem` | declared memory budget |
| 8 | `constitutional_score` | rolling CONSTITUTIONAL score |
| 9 | `federation_trust_score` | FEDERATION_TRUST score |
| 10 | `violation_rate_7d` | rolling 7-day violation rate |
| 11 | `escalation_history` | log-normalised escalation count |

### AlignmentMonitor score features (8 dimensions)

| # | Feature | Description |
|---|---------|-------------|
| 0–4 | `dimension_id` | 5-bit one-hot over AlignmentDimension |
| 5 | `window_size_s` | log-normalised scoring window |
| 6 | `sample_count` | log-normalised sample count |
| 7 | `recent_trend` | slope of last 5 samples |

---

## `InterpretabilityProbe` Protocol

```python
class InterpretabilityProbe(Protocol):
    async def explain(
        self,
        target: ExplanationTarget,
        subject_id: str,
        feature_vector: Sequence[float],
        decision_value: float,
        *,
        method: AttributionMethod | None = None,
    ) -> ProbeExplanation: ...

    async def batch_explain(
        self,
        requests: Sequence[tuple[ExplanationTarget, str, Sequence[float], float]],
    ) -> tuple[ProbeExplanation, ...]: ...

    def get_explanation(self, explanation_id: str) -> ProbeExplanation | None: ...

    async def snapshot(self) -> ProbeSnapshot: ...
```

---

## `InMemoryInterpretabilityProbe`

### `__init__()`

```python
def __init__(self, config: ProbeConfig) -> None:
    self._config = config
    self._cache: dict[str, ProbeExplanation] = {}
    self._cache_access: dict[str, float] = {}
    self._total_explanations: int = 0
    self._cache_hits: int = 0
    self._method_counts: Counter[AttributionMethod] = Counter()
    self._target_counts: Counter[ExplanationTarget] = Counter()
    self._attribution_ms: list[float] = []
    self._lock = asyncio.Lock()
```

### `_cache_key()` — deterministic fingerprint

```python
def _cache_key(
    self, target: ExplanationTarget, subject_id: str, feature_vector: Sequence[float]
) -> str:
    raw = f"{target.value}:{subject_id}:{tuple(round(x, 6) for x in feature_vector)!r}"
    return sha256(raw.encode()).hexdigest()[:16]
```

Round to 6 decimal places prevents floating-point jitter cache misses.

### `_permutation_attribution()` — zero-baseline ablation

```python
async def _permutation_attribution(
    self,
    feature_vector: Sequence[float],
    decision_value: float,
    baseline_fn: Callable[[Sequence[float]], float],
) -> tuple[FeatureAttribution, ...]:
    raw: list[tuple[int, float]] = []
    for i in range(len(feature_vector)):
        ablated = list(feature_vector)
        ablated[i] = 0.0
        delta = decision_value - baseline_fn(ablated)
        raw.append((i, delta))
    total = sum(abs(d) for _, d in raw) or 1.0
    return tuple(
        FeatureAttribution(
            feature_name=FEATURE_NAMES.get(i, f"feature_{i}"),
            attribution_score=delta,
            relative_importance=abs(delta) / total,
        )
        for i, delta in sorted(raw, key=lambda x: -abs(x[1]))[: self._config.top_k_features]
    )
```

### `_integrated_grad_attribution()` — 50-step Riemann sum

```python
async def _integrated_grad_attribution(
    self, feature_vector: Sequence[float], decision_value: float
) -> tuple[FeatureAttribution, ...]:
    n = len(feature_vector)
    baseline = [0.0] * n
    steps = 50
    grads = [0.0] * n
    for s in range(1, steps + 1):
        alpha = s / steps
        interp = [baseline[i] + alpha * (feature_vector[i] - baseline[i]) for i in range(n)]
        for i in range(n):
            grads[i] += (interp[i] - baseline[i]) / steps
    total = sum(abs(g) for g in grads) or 1.0
    return tuple(
        FeatureAttribution(
            feature_name=FEATURE_NAMES.get(i, f"feature_{i}"),
            attribution_score=g,
            relative_importance=abs(g) / total,
        )
        for i, g in sorted(enumerate(grads), key=lambda x: -abs(x[1]))[: self._config.top_k_features]
    )
```

### `_build_counterfactual()`

```python
def _build_counterfactual(
    self, attributions: tuple[FeatureAttribution, ...], decision_value: float
) -> tuple[str, ...] | None:
    flips = [
        a.feature_name
        for a in sorted(attributions, key=lambda x: x.attribution_score)
        [: self._config.counterfactual_max_flips]
    ]
    return tuple(flips) if flips else None
```

### `explain()` — cache check → dispatch → store → metrics

```python
async def explain(
    self,
    target: ExplanationTarget,
    subject_id: str,
    feature_vector: Sequence[float],
    decision_value: float,
    *,
    method: AttributionMethod | None = None,
) -> ProbeExplanation:
    method = method or self._config.method
    cache_key = self._cache_key(target, subject_id, feature_vector)

    async with self._lock:
        now = time.monotonic()
        if cache_key in self._cache:
            age = now - self._cache_access.get(cache_key, 0)
            if age < self._config.cache_ttl_s:
                self._cache_hits += 1
                PROBE_CACHE_HITS.inc()
                return self._cache[cache_key]

        t0 = time.perf_counter()
        if method == AttributionMethod.PERMUTATION:
            attributions = await self._permutation_attribution(
                feature_vector, decision_value,
                lambda fv: sum(w * x for w, x in zip(feature_vector, fv)) / max(len(fv), 1),
            )
        else:
            attributions = await self._integrated_grad_attribution(feature_vector, decision_value)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        counterfactual = self._build_counterfactual(attributions, decision_value)
        confidence = min(1.0, len(attributions) / max(self._config.top_k_features, 1))

        explanation = ProbeExplanation(
            explanation_id=str(uuid4()),
            target=target,
            subject_id=subject_id,
            method=method,
            decision_value=decision_value,
            attributions=attributions,
            counterfactual=counterfactual,
            confidence=confidence,
            generated_at=time.time(),
        )

        # TTL + LRU eviction
        expired = [k for k, t in self._cache_access.items() if now - t > self._config.cache_ttl_s]
        for k in expired:
            self._cache.pop(k, None); self._cache_access.pop(k, None)
        while len(self._cache) >= self._config.max_cache_entries:
            oldest = min(self._cache_access, key=self._cache_access.get)
            del self._cache[oldest], self._cache_access[oldest]

        self._cache[cache_key] = explanation
        self._cache_access[cache_key] = now
        self._total_explanations += 1
        self._method_counts[method] += 1
        self._target_counts[target] += 1
        self._attribution_ms.append(elapsed_ms)

        PROBE_EXPLANATIONS.labels(target=target.value, method=method.value).inc()
        PROBE_ATTRIBUTION_MS.observe(elapsed_ms)
        PROBE_CACHE_SIZE.set(len(self._cache))

        return explanation
```

### `batch_explain()`

```python
async def batch_explain(
    self,
    requests: Sequence[tuple[ExplanationTarget, str, Sequence[float], float]],
) -> tuple[ProbeExplanation, ...]:
    results = await asyncio.gather(
        *(self.explain(t, sid, fv, dv) for t, sid, fv, dv in requests)
    )
    return tuple(results)
```

### `snapshot()`

```python
async def snapshot(self) -> ProbeSnapshot:
    async with self._lock:
        total = self._total_explanations or 1
        return ProbeSnapshot(
            total_explanations=self._total_explanations,
            cache_hit_rate=self._cache_hits / total,
            method_distribution=tuple(
                (m.value, c) for m, c in self._method_counts.items()
            ),
            target_distribution=tuple(
                (t.value, c) for t, c in self._target_counts.items()
            ),
            avg_attribution_compute_ms=(
                sum(self._attribution_ms) / len(self._attribution_ms)
                if self._attribution_ms else 0.0
            ),
            snapshot_at=time.time(),
        )
```

---

## Factory function

```python
def build_interpretability_probe(
    config: ProbeConfig | None = None,
) -> InterpretabilityProbe:
    return InMemoryInterpretabilityProbe(config or ProbeConfig())
```

---

## `CognitiveCycle` integration

```python
class CognitiveCycle:
    async def _explain_safety_verdict(
        self,
        goal_id: str,
        feature_vector: Sequence[float],
        verdict_score: float,
    ) -> None:
        explanation = await self._probe.explain(
            ExplanationTarget.SAFETY_VERDICT,
            goal_id,
            feature_vector,
            verdict_score,
        )
        await self._blackboard.write(
            f"explanation:{goal_id}",
            {
                "top_features": [
                    {"name": a.feature_name, "score": round(a.attribution_score, 4)}
                    for a in explanation.attributions[:5]
                ],
                "counterfactual": list(explanation.counterfactual or []),
                "confidence": round(explanation.confidence, 3),
            },
        )
```

---

## Prometheus metrics (5 metrics)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_probe_explanations_total` | Counter | target, method | explanations generated |
| `asi_probe_cache_hits_total` | Counter | — | cache hits |
| `asi_probe_cache_size` | Gauge | — | current cache entries |
| `asi_probe_attribution_ms` | Histogram | — | attribution computation time (ms) |
| `asi_probe_confidence_score` | Histogram | target | explanation confidence [0, 1] |

### PromQL

```promql
# Explanation throughput
rate(asi_probe_explanations_total[5m])

# Cache hit rate
rate(asi_probe_cache_hits_total[5m]) / rate(asi_probe_explanations_total[5m])

# P95 attribution latency
histogram_quantile(0.95, rate(asi_probe_attribution_ms_bucket[5m]))

# Mean confidence by target
avg by (target) (rate(asi_probe_confidence_score_sum[5m]) / rate(asi_probe_confidence_score_count[5m]))
```

---

## mypy compliance

| Symbol | Annotation |
|--------|-----------|
| `ProbeExplanation.attributions` | `tuple[FeatureAttribution, ...]` |
| `InMemoryInterpretabilityProbe._cache` | `dict[str, ProbeExplanation]` |
| `explain()` return | `ProbeExplanation` |
| `batch_explain()` return | `tuple[ProbeExplanation, ...]` |
| `feature_vector` param | `Sequence[float]` |
| `counterfactual` field | `tuple[str, ...] \| None` |
| `_method_counts` | `Counter[AttributionMethod]` |

---

## Test targets (12 tests)

| # | Test | Covers |
|---|------|--------|
| 1 | `test_explain_permutation_returns_top_k` | attributions capped at `top_k_features` |
| 2 | `test_explain_integrated_grad_returns_explanations` | all features have attributions |
| 3 | `test_cache_hit_returns_same_explanation_id` | identical input → same `explanation_id` |
| 4 | `test_cache_ttl_eviction` | expired entry regenerated after TTL |
| 5 | `test_cache_lru_eviction` | oldest entry evicted at `max_cache_entries` |
| 6 | `test_counterfactual_top_negative_features` | counterfactual lists negative-attribution features |
| 7 | `test_confidence_clipped_to_one` | confidence never exceeds 1.0 |
| 8 | `test_batch_explain_parallel` | batch processes all requests via gather |
| 9 | `test_snapshot_totals_consistent` | snapshot counts match internal state |
| 10 | `test_method_override` | per-call method overrides config default |
| 11 | `test_safety_verdict_target` | `SAFETY_VERDICT` correctly routed |
| 12 | `test_alignment_score_target` | `ALIGNMENT_SCORE` correctly routed |

---

## Implementation order (14 steps)

1. `AttributionMethod` + `ExplanationTarget` enums
2. `FeatureAttribution` frozen dataclass
3. `ProbeExplanation` frozen dataclass
4. `ProbeConfig` + `ProbeSnapshot` frozen dataclasses
5. `FEATURE_NAMES: dict[int, str]` module-level mapping
6. Prometheus metrics pre-init (5 metrics)
7. `InterpretabilityProbe` Protocol
8. `InMemoryInterpretabilityProbe.__init__()`
9. `_cache_key()` — sha256 hash with rounding
10. `_permutation_attribution()` — zero-baseline ablation loop
11. `_integrated_grad_attribution()` — 50-step Riemann sum
12. `_build_counterfactual()` — top-k negative attribution features
13. `explain()` + `batch_explain()` + `get_explanation()` + `snapshot()`
14. `build_interpretability_probe()` factory + `CognitiveCycle._explain_safety_verdict()`

---

## Phase 11 roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 11.1 | SafetyFilter | [#337](https://github.com/web3guru888/asi-build/issues/337) | ✅ spec'd |
| 11.2 | AlignmentMonitor | [#340](https://github.com/web3guru888/asi-build/issues/340) | ✅ spec'd |
| 11.3 | ValueLearner | [#343](https://github.com/web3guru888/asi-build/issues/343) | ✅ spec'd |
| 11.4 | InterpretabilityProbe | [#346](https://github.com/web3guru888/asi-build/issues/346) | ✅ spec'd |
| 11.5 | AlignmentDashboard | planned | ⏳ next |
