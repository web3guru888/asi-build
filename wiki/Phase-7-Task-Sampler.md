# Phase 7.2 — Task Distribution Sampler

**Phase**: 7.2 | **Depends on**: Phase 7.1 (ReptileMetaLearner), Phase 6.5 (TaskRegistry)

Phase 7.2 introduces structured task sampling for the Reptile meta-learning loop. The quality of a meta-learned prior depends heavily on which tasks the learner sees and in what order — this sub-phase provides four sampling strategies with curriculum support.

---

## Why task sampling matters

```
Reptile prior quality = f(task diversity, task difficulty schedule, task balance)
```

| Sampling factor | Effect on convergence | Effect on generalisation |
|---|---|---|
| Uniform random | Moderate | Good broad coverage |
| Curriculum (easy→hard) | 2-3x faster early | Comparable final quality |
| Difficulty-weighted | Variable | Focused on hard tasks |
| Recency-weighted | Steady | Prevents easy-task forgetting |

---

## New Components

### `SamplingStrategy` (str enum)

```python
class SamplingStrategy(str, Enum):
    UNIFORM             = "uniform"             # equal probability per task
    CURRICULUM          = "curriculum"          # difficulty ceiling annealing
    DIFFICULTY_WEIGHTED = "difficulty_weighted" # sample proportional to difficulty
    RECENCY_WEIGHTED    = "recency_weighted"    # sample proportional to staleness
```

Using `str` mixin allows YAML/JSON config to pass strategy as a plain string.

---

### `TaskProvider` (Protocol)

```python
class TaskProvider(Protocol):
    async def __call__(self, *, rng: np.random.Generator) -> TaskSample: ...
    
    @property
    def difficulty(self) -> float:
        # Difficulty estimate in [0.0, 1.0].
        ...
```

Any async callable returning a `TaskSample` satisfies the Protocol. Existing task generators only need a `difficulty` property added.

---

### `CurriculumScheduler`

Implements the self-paced learning schedule:

```
ceiling(t) = min(1.0, start_ceiling + slope * max(0, t - warmup_steps))
```

```python
class CurriculumScheduler:
    def __init__(
        self,
        start_ceiling: float = 0.3,
        slope: float = 0.01,
        warmup_steps: int = 100,
    ) -> None: ...
    
    def ceiling(self, step: int) -> float: ...
    
    def eligible_tasks(
        self,
        task_difficulties: Mapping[str, float],
        step: int,
    ) -> frozenset[str]: ...
```

**Ceiling trajectory** (start=0.3, slope=0.01, warmup=100):

| Step | Ceiling | Approx eligible (uniform difficulties) |
|---|---|---|
| 0 | 0.30 | ~30% |
| 100 | 0.30 | ~30% (warmup plateau) |
| 120 | 0.50 | ~50% |
| 170 | 1.00 | 100% |

---

### `TaskSampler`

```python
class TaskSampler:
    def __init__(
        self,
        task_pool: Mapping[str, TaskProvider],
        strategy: SamplingStrategy = SamplingStrategy.UNIFORM,
        batch_size: int = 4,
        loss_scale: float = 1.0,
        allow_repeats: bool = True,
        seed: int | None = None,
        scheduler: CurriculumScheduler | None = None,
        metrics_registry: CollectorRegistry | None = None,
    ) -> None: ...
    
    async def sample_batch(self) -> list[TaskSample]: ...
    
    def update_difficulty(self, task_id: str, loss: float) -> None:
        # EMA-update difficulty from observed inner-loop loss.
        ...
    
    def register_task(self, task_id: str, provider: TaskProvider, difficulty: float = 0.5) -> None: ...
    def deregister_task(self, task_id: str) -> None: ...
    def snapshot(self) -> SamplerSnapshot: ...
    def restore(self, snap: SamplerSnapshot) -> None: ...
```

---

### `SamplerSnapshot` (dataclass)

```python
@dataclass
class SamplerSnapshot:
    task_difficulties:  dict[str, float]
    sample_counts:      dict[str, int]
    step:               int
    strategy:           SamplingStrategy
    timestamp:          float
```

---

## Difficulty EMA update

```
difficulty_t = alpha * clip(loss / loss_scale, 0, 1) + (1 - alpha) * difficulty_{t-1}
```

- **alpha = 0.2** — smooths noisy single-episode loss estimates
- **loss_scale** — normalises raw loss to [0, 1]; set to expected nominal loss magnitude

```python
EMA_ALPHA = 0.2

def update_difficulty(self, task_id: str, loss: float) -> None:
    clamped = min(1.0, max(0.0, loss / self._loss_scale))
    prev = self._difficulties.get(task_id, 0.5)
    self._difficulties[task_id] = EMA_ALPHA * clamped + (1 - EMA_ALPHA) * prev
    self._difficulty_gauge.labels(task_id=self._task_label(task_id)).set(
        self._difficulties[task_id]
    )
```

---

## Sampling strategy implementations

### UNIFORM
```python
chosen = self._rng.choice(eligible_list, size=batch_size, replace=self._allow_repeats)
```

### CURRICULUM (easy-first with fallback)
```python
eligible = self._scheduler.eligible_tasks(self._difficulties, self._step)
if not eligible:
    # Fallback: never raise — use the single easiest task
    easiest = min(self._difficulties, key=self._difficulties.get)
    eligible = frozenset([easiest])
chosen = self._rng.choice(list(eligible), size=batch_size, replace=self._allow_repeats)
```

### DIFFICULTY_WEIGHTED (hard tasks sampled more)
```python
weights = np.array([self._difficulties.get(t, 0.5) for t in eligible_list])
weights = weights / weights.sum()
chosen = self._rng.choice(eligible_list, size=batch_size, replace=True, p=weights)
```

### RECENCY_WEIGHTED (stale tasks sampled more)
```python
staleness = np.array([self._steps_since_sampled.get(t, 0) for t in eligible_list], dtype=float)
exp_s = np.exp(staleness - staleness.max())        # softmax for numerical stability
weights = exp_s / exp_s.sum()
chosen = self._rng.choice(eligible_list, size=batch_size, replace=True, p=weights)
for t in chosen:
    self._steps_since_sampled[t] = 0              # reset recency counter
```

---

## Integration with Phase 7.1 (SLEEP_PHASE hook)

```python
# In MemoryConsolidator._sleep_phase_hook():
async def _sleep_phase_hook(self, step: int) -> None:
    await self._fisher_acc.force_snapshot()              # Phase 6.4
    await self._ewc.consolidate()                        # Phase 6.1
    self._task_registry.evict_lru()                      # Phase 6.5
    
    batch = await self._task_sampler.sample_batch()      # Phase 7.2
    result = await self._meta_learner.meta_update(batch) # Phase 7.1
    
    for task_sample, loss in zip(batch, result.inner_losses):
        self._task_sampler.update_difficulty(task_sample.task_id, loss)
    self._task_sampler._step += 1
```

---

## Prometheus metrics (5)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_task_sampler_batches_total` | Counter | — | Total `sample_batch()` calls |
| `asi_task_sampler_tasks_sampled_total` | Counter | `task_id` | Per-task sample count |
| `asi_task_difficulty` | Gauge | `task_id` | EMA difficulty estimate |
| `asi_curriculum_ceiling` | Gauge | — | Current difficulty ceiling |
| `asi_task_sampler_eligible_tasks` | Gauge | — | Eligible task count at current ceiling |

All 5 metrics must be initialised in `__init__` with `.inc(0)` / `.set(0)` to prevent `KeyError` on first scrape.

### PromQL

```promql
# Current curriculum ceiling
asi_curriculum_ceiling

# Eligible tasks right now (alert if 0)
asi_task_sampler_eligible_tasks == 0

# Per-task sampling rate (5-min)
rate(asi_task_sampler_tasks_sampled_total[5m])

# Single task monopolising > 80% of batches
rate(asi_task_sampler_tasks_sampled_total{task_id!="other"}[5m])
  / rate(asi_task_sampler_batches_total[5m]) > 0.8
```

---

## Test targets (12)

| # | Test | File |
|---|---|---|
| 1 | `test_uniform_sampling_distributes_evenly` | test_task_sampler.py |
| 2 | `test_curriculum_blocks_high_difficulty_tasks` | test_task_sampler.py |
| 3 | `test_curriculum_unblocks_as_ceiling_rises` | test_task_sampler.py |
| 4 | `test_difficulty_weighted_favours_high_loss_tasks` | test_task_sampler.py |
| 5 | `test_recency_weighted_avoids_recently_sampled` | test_task_sampler.py |
| 6 | `test_update_difficulty_clamps_to_unit_interval` | test_task_sampler.py |
| 7 | `test_register_task_adds_to_pool` | test_task_sampler.py |
| 8 | `test_deregister_task_removes_from_pool` | test_task_sampler.py |
| 9 | `test_sample_batch_respects_batch_size` | test_task_sampler.py |
| 10 | `test_sampler_snapshot_round_trip` | test_task_sampler.py |
| 11 | `test_prometheus_metrics_pre_init` | test_task_sampler.py |
| 12 | `test_curriculum_scheduler_warmup` | test_curriculum.py |

---

## Implementation order (10 steps)

1. `SamplingStrategy` enum + `SamplerSnapshot` dataclass (additions to `meta_types.py`)
2. `TaskProvider` Protocol (`task_provider.py`)
3. `CurriculumScheduler` — `ceiling()` + `eligible_tasks()` (`task_provider.py`)
4. `TaskSampler.__init__` — pool registration, RNG seeding, Prometheus pre-init (5 metrics)
5. `TaskSampler.sample_batch()` — UNIFORM and CURRICULUM strategies
6. `TaskSampler.sample_batch()` — DIFFICULTY_WEIGHTED and RECENCY_WEIGHTED strategies
7. `TaskSampler.update_difficulty()` — EMA + Prometheus gauge update
8. `TaskSampler.register_task / deregister_task`
9. `TaskSampler.snapshot() / restore()` — SamplerSnapshot serialisation
10. Tests — 12 targets across `test_task_sampler.py` and `test_curriculum.py`

---

## Phase 7 roadmap

| Sub-phase | Component | Status |
|---|---|---|
| 7.1 | `ReptileMetaLearner`, `TaskSample`, `MetaParamSnapshot` | Open (#259) |
| **7.2** | **`TaskSampler`, `CurriculumScheduler`, `TaskProvider`** | **Open (#262)** |
| 7.3 | N-way K-shot few-shot evaluation harness | Planned |
| 7.4 | Meta-checkpoint store (persist/restore meta-params) | Planned |
| 7.5 | Meta-learning integration tests | Planned |

---

*See also: [[Phase-7-Meta-Learning]] | [[Phase-6-Multi-Task-EWC]] | [[Home]]*
