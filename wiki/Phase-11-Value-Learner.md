# Phase 11.3 — ValueLearner

**Phase**: 11 — Safety & Alignment
**Issue**: [#343](https://github.com/web3guru888/asi-build/issues/343)
**Depends on**: [Phase 11.2 — AlignmentMonitor](Phase-11-Alignment-Monitor), [Phase 11.1 — SafetyFilter](Phase-11-Safety-Filter)
**Discussions**: [#344 (Show & Tell)](https://github.com/web3guru888/asi-build/discussions/344) · [#345 (Q&A)](https://github.com/web3guru888/asi-build/discussions/345)

---

## Motivation

`AlignmentMonitor` (#340) provides continuous alignment health scoring against pre-defined constitutional dimensions. `ValueLearner` closes the human-in-the-loop: it captures explicit feedback signals (approve / reject / adjust) from human operators and federation peers, fits a lightweight reward model from those signals, and propagates updated value weights back into the `SafetyFilter` ruleset and `AlignmentMonitor` dimension thresholds.

Without `ValueLearner`, alignment rules are static — they can only be updated by manual config changes. With `ValueLearner`, the system learns *which behaviors humans actually prefer* rather than relying solely on upfront rule authorship.

---

## `FeedbackSignal` Enum (6 types)

```python
class FeedbackSignal(StrEnum):
    APPROVE           = "approve"          # human explicitly approves action
    REJECT            = "reject"           # human explicitly rejects action
    ADJUST_WEIGHT     = "adjust_weight"    # direct scalar weight nudge
    COMPARATIVE       = "comparative"      # prefer A over B (pair ranking)
    IMPLICIT_POSITIVE = "implicit_pos"    # inferred from positive outcome
    IMPLICIT_NEGATIVE = "implicit_neg"    # inferred from negative outcome
```

| Signal | Source | Regression Target | Use Case |
|--------|--------|-------------------|----------|
| `APPROVE` | Human operator | `+1.0` | Explicit endorsement of completed goal |
| `REJECT` | Human operator | `-1.0` | Explicit veto of goal/action |
| `ADJUST_WEIGHT` | Human/API | `entry.value` | Direct scalar nudge to dimension weight |
| `COMPARATIVE` | Human (pairwise) | ranking loss | Prefer strategy A over B |
| `IMPLICIT_POSITIVE` | `CognitiveCycle` | `+0.7` | Goal completed successfully |
| `IMPLICIT_NEGATIVE` | `CognitiveCycle` | `-0.5` | Goal abandoned / failed |

---

## Frozen Dataclasses

```python
@dataclass(frozen=True)
class FeedbackEntry:
    entry_id: str                    # UUID
    goal_id: str
    dimension: AlignmentDimension    # which alignment axis
    signal: FeedbackSignal
    value: float                     # scalar in [-1.0, 1.0]
    annotator_id: str                # human or peer DID
    timestamp: float                 # epoch seconds
    context_hash: str                # sha256[:16] of (goal_id + task_ids)

@dataclass(frozen=True)
class RewardModelWeights:
    weights: tuple[float, ...]       # len == 5 (one per AlignmentDimension)
    bias: float
    version: int
    trained_at: float
    sample_count: int

@dataclass(frozen=True)
class ValueLearnerConfig:
    learning_rate: float = 0.01
    regularisation_lambda: float = 1e-4
    min_feedback_to_train: int = 10   # minimum samples before first update
    max_history: int = 10_000         # FIFO eviction of oldest feedback
    update_interval_s: float = 60.0   # background model update period
    comparative_margin: float = 0.1   # margin for comparative ranking loss

@dataclass(frozen=True)
class ValueLearnerSnapshot:
    total_feedback: int
    model_version: int
    weights: tuple[float, ...]
    bias: float
    last_trained_at: float | None
    pending_feedback: int
```

---

## `ValueLearner` Protocol

```python
class ValueLearner(Protocol):
    async def record_feedback(self, entry: FeedbackEntry) -> None: ...
    async def train(self) -> RewardModelWeights: ...
    async def score(self, dimension: AlignmentDimension, context_hash: str) -> float: ...
    def current_weights(self) -> RewardModelWeights: ...
    def snapshot(self) -> ValueLearnerSnapshot: ...
```

---

## `InMemoryValueLearner` Implementation

### Fields

```python
class InMemoryValueLearner:
    _config: ValueLearnerConfig
    _history: collections.deque[FeedbackEntry]   # maxlen=max_history
    _weights: list[float]                        # len == 5, one per AlignmentDimension
    _bias: float
    _version: int
    _last_trained_at: float | None
    _pending: list[FeedbackEntry]                # since last train() call
    _lock: asyncio.Lock
    _bg_task: asyncio.Task | None
```

### `_DIM_INDEX` — Dimension Mapping

```python
_DIM_INDEX: dict[AlignmentDimension, int] = {
    d: i for i, d in enumerate(AlignmentDimension)
}

# AlignmentDimension order:
# 0: CONSTITUTIONAL, 1: CAPABILITY_SCOPE, 2: GOAL_PRIORITY,
# 3: RESOURCE_USAGE,  4: FEDERATION_TRUST
```

### `record_feedback(entry)`

```python
async def record_feedback(self, entry: FeedbackEntry) -> None:
    async with self._lock:
        self._history.append(entry)   # deque auto-evicts oldest at maxlen
        self._pending.append(entry)
    VALUE_LEARNER_FEEDBACK_TOTAL.labels(signal=entry.signal.value).inc()
    VALUE_LEARNER_PENDING_FEEDBACK.set(len(self._pending))
```

### `_feature_vector(entry) -> list[float]`

```python
def _feature_vector(self, entry: FeedbackEntry) -> list[float]:
    vec = [0.0] * 5
    vec[_DIM_INDEX[entry.dimension]] = 1.0
    vec.append(entry.value)   # 6th element: scalar signal magnitude
    return vec
```

### `_signal_to_target(signal, value) -> float`

```python
_SIGNAL_TARGETS: dict[FeedbackSignal, float | None] = {
    FeedbackSignal.APPROVE:            1.0,
    FeedbackSignal.REJECT:            -1.0,
    FeedbackSignal.IMPLICIT_POSITIVE:  0.7,
    FeedbackSignal.IMPLICIT_NEGATIVE: -0.5,
    FeedbackSignal.ADJUST_WEIGHT:      None,   # use entry.value directly
    FeedbackSignal.COMPARATIVE:        None,   # handled in ranking pass
}
```

### `train() -> RewardModelWeights`

```python
async def train(self) -> RewardModelWeights:
    async with self._lock:
        if len(self._history) < self._config.min_feedback_to_train:
            return self.current_weights()

        lr, lam = self._config.learning_rate, self._config.regularisation_lambda
        batch = list(self._pending)
        t0 = time.monotonic()

        # MSE pass (non-comparative)
        for entry in batch:
            if entry.signal == FeedbackSignal.COMPARATIVE:
                continue
            x = self._feature_vector(entry)
            pred = sum(w * f for w, f in zip(self._weights, x[:5])) + self._bias
            target = _signal_to_target(entry.signal, entry.value)
            err = pred - target
            for i in range(5):
                self._weights[i] -= lr * (err * x[i] + lam * self._weights[i])
            self._bias -= lr * err

        # Ranking loss pass (comparative pairs)
        comparatives = [e for e in batch if e.signal == FeedbackSignal.COMPARATIVE]
        for i in range(0, len(comparatives) - 1, 2):
            pref, rej = comparatives[i], comparatives[i + 1]
            fp, fr = self._feature_vector(pref), self._feature_vector(rej)
            s_pref = sum(w * f for w, f in zip(self._weights, fp[:5])) + self._bias
            s_rej  = sum(w * f for w, f in zip(self._weights, fr[:5])) + self._bias
            if s_rej - s_pref + self._config.comparative_margin > 0:
                for j in range(5):
                    self._weights[j] -= lr * (fr[j] - fp[j])

        # Stability guard
        self._weights = [max(-2.0, min(2.0, w)) for w in self._weights]

        self._version += 1
        self._last_trained_at = time.time()
        self._pending.clear()

        VALUE_LEARNER_MODEL_VERSION.set(self._version)
        VALUE_LEARNER_TRAIN_DURATION.observe(time.monotonic() - t0)
        VALUE_LEARNER_WEIGHT_NORM.set(math.sqrt(sum(w**2 for w in self._weights)))
        VALUE_LEARNER_PENDING_FEEDBACK.set(0)

        return RewardModelWeights(
            weights=tuple(self._weights),
            bias=self._bias,
            version=self._version,
            trained_at=self._last_trained_at,
            sample_count=len(self._history),
        )
```

### `score(dimension, context_hash) -> float`

```python
async def score(self, dimension: AlignmentDimension, context_hash: str) -> float:
    raw = self._weights[_DIM_INDEX[dimension]] * 1.0 + self._bias
    return max(0.0, min(1.0, raw))
```

### `_bg_update_loop()`

```python
async def _bg_update_loop(self) -> None:
    while True:
        await asyncio.sleep(self._config.update_interval_s)
        weights = await self.train()
        logger.info(
            "value_learner.bg_train",
            model_version=weights.version,
            sample_count=weights.sample_count,
        )
```

### `start() / stop()`

```python
async def start(self) -> None:
    self._bg_task = asyncio.create_task(self._bg_update_loop())

async def stop(self) -> None:
    if self._bg_task:
        self._bg_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._bg_task
```

### `snapshot()`

```python
def snapshot(self) -> ValueLearnerSnapshot:
    return ValueLearnerSnapshot(
        total_feedback=len(self._history),
        model_version=self._version,
        weights=tuple(self._weights),
        bias=self._bias,
        last_trained_at=self._last_trained_at,
        pending_feedback=len(self._pending),
    )
```

---

## Factory

```python
def build_value_learner(config: ValueLearnerConfig | None = None) -> ValueLearner:
    return InMemoryValueLearner(config or ValueLearnerConfig())
```

---

## `CognitiveCycle` Integration

```python
class CognitiveCycle:
    _value_learner: ValueLearner

    async def _handle_goal_outcome(self, goal: Goal, outcome: GoalStatus) -> None:
        signal = (
            FeedbackSignal.IMPLICIT_POSITIVE if outcome == GoalStatus.COMPLETED
            else FeedbackSignal.IMPLICIT_NEGATIVE
        )
        for dim in AlignmentDimension:
            await self._value_learner.record_feedback(FeedbackEntry(
                entry_id=str(uuid4()),
                goal_id=goal.goal_id,
                dimension=dim,
                signal=signal,
                value=1.0 if signal == FeedbackSignal.IMPLICIT_POSITIVE else -0.5,
                annotator_id="cognitive_cycle",
                timestamp=time.time(),
                context_hash=hashlib.sha256(goal.goal_id.encode()).hexdigest()[:16],
            ))
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `value_learner_feedback_total` | Counter | Total entries recorded, by `signal` label |
| `value_learner_model_version` | Gauge | Current reward model version |
| `value_learner_train_duration_seconds` | Histogram | Time spent in `train()` |
| `value_learner_pending_feedback` | Gauge | Entries since last `train()` |
| `value_learner_weight_norm` | Gauge | L2 norm of current weight vector |

### PromQL Examples

```promql
# Feedback intake rate by signal type
rate(value_learner_feedback_total[5m])

# Model freshness (seconds since last train)
time() - value_learner_last_trained_timestamp

# Weight drift alert
delta(value_learner_weight_norm[1h]) > 0.5
```

### Grafana Alert

```yaml
alert: ValueLearnerWeightDrift
expr: delta(value_learner_weight_norm[30m]) > 0.5
for: 5m
labels:
  severity: warning
annotations:
  summary: "ValueLearner weights drifting — review recent feedback quality"
```

---

## mypy Compliance

| Symbol | Notes |
|--------|-------|
| `FeedbackSignal` | `StrEnum` |
| `FeedbackEntry` | `frozen=True`, all fields typed |
| `RewardModelWeights` | `tuple[float, ...]` (immutable) |
| `ValueLearnerConfig` | `frozen=True`, defaults typed |
| `ValueLearner` | `Protocol` with `runtime_checkable` |
| `InMemoryValueLearner` | `asyncio.Lock`, `deque[FeedbackEntry]` |
| `_bg_task: asyncio.Task | None` | union with `None` sentinel |
| `build_value_learner` | returns `ValueLearner` (structural subtype) |

---

## Test Targets (12)

1. `test_record_feedback_appends_to_history`
2. `test_history_evicts_oldest_at_maxlen`
3. `test_train_skips_below_min_feedback`
4. `test_train_returns_frozen_weights`
5. `test_train_increments_version`
6. `test_score_clamps_to_unit_interval`
7. `test_approve_signal_increases_dimension_weight`
8. `test_reject_signal_decreases_dimension_weight`
9. `test_comparative_signal_rank_order`
10. `test_bg_update_loop_calls_train`
11. `test_snapshot_reflects_state`
12. `test_weight_clip_prevents_divergence`

---

## Implementation Order (14 steps)

1. Define `FeedbackSignal` enum
2. Define frozen dataclasses (`FeedbackEntry`, `RewardModelWeights`, `ValueLearnerConfig`, `ValueLearnerSnapshot`)
3. Define `ValueLearner` Protocol
4. Define `_DIM_INDEX` mapping constant
5. Stub `InMemoryValueLearner.__init__` with all fields
6. Implement `record_feedback()` with `asyncio.Lock` + deque
7. Implement `_feature_vector()` one-hot encoder
8. Implement `_signal_to_target()` helper + `_SIGNAL_TARGETS` map
9. Implement `train()` MSE gradient pass
10. Implement `train()` comparative ranking loss pass + weight clipping
11. Implement `score()` linear scorer + clamp
12. Implement `_bg_update_loop()` asyncio task
13. Implement `start()` / `stop()` lifecycle
14. Implement `snapshot()` + `build_value_learner()` factory + Prometheus pre-registration

---

## Phase 11 Sub-Phase Roadmap

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| 11.1 | SafetyFilter — constitutional ruleset gating | ✅ [Spec filed (#337)](https://github.com/web3guru888/asi-build/issues/337) |
| 11.2 | AlignmentMonitor — continuous drift detection | ✅ [Spec filed (#340)](https://github.com/web3guru888/asi-build/issues/340) |
| 11.3 | ValueLearner — reward model from human feedback | 🟡 This page |
| 11.4 | InterpretabilityProbe — activation patching & steering | 📋 Planned |
| 11.5 | AlignmentDashboard — unified safety/alignment UI | 📋 Planned |
