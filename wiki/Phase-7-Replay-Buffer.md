# Phase 7.3 — Prioritised Episodic Replay Buffer

**Status**: 🟡 Specification — [Issue #265](https://github.com/web3guru888/asi-build/issues/265)
**Discussions**: [Show & Tell #267](https://github.com/web3guru888/asi-build/discussions/267) · [Q&A #268](https://github.com/web3guru888/asi-build/discussions/268)
**Depends on**: Phase 7.1 (ReptileMetaLearner), Phase 7.2 (TaskSampler), Phase 6.3 (EWCRegulariser)
**Module**: `asi/phase7/replay_buffer.py`

---

## Motivation

Catastrophic forgetting occurs when new task gradients overwrite weights learned for previous tasks. Phase 6 addresses this via Fisher-weighted parameter penalties (EWC). Phase 7.1 addresses it via meta-learning (Reptile). Phase 7.3 adds a third, complementary mechanism: **episodic replay** — storing past experiences and interleaving them with live training.

| Mechanism | Operates On | When |
|---|---|---|
| EWC (Phase 6) | Parameter importance | Weight update time |
| Reptile (Phase 7.1) | Meta-weights | SLEEP_PHASE |
| Task Sampler (Phase 7.2) | Which task to run | Episode start |
| **Replay (Phase 7.3)** | **Past episode gradients** | **Every update step** |

---

## Prioritised Experience Replay (PER)

Replay buffers store past `Episode` tuples and sample from them during training. **Prioritised** replay over-samples high-error episodes (where the agent has most to learn), then corrects the resulting bias with importance-sampling (IS) weights.

### Sampling probability

```
P(i) = p_i^α / Σ_j p_j^α
```

Where `p_i = |δ_i| + ε` is the TD-error (or loss) magnitude for episode `i`, `α ∈ [0,1]` controls prioritisation strength, and `ε` is a small constant to keep all priorities positive.

| `α` | Effect |
|---|---|
| 0.0 | Uniform sampling (≡ `UniformReplayBuffer`) |
| 0.4 | Mild prioritisation |
| **0.6** | **Standard PER (default)** |
| 1.0 | Fully greedy — highest-priority only |

### IS correction weights

Prioritised sampling introduces bias; IS weights correct it:

```
w_i = (N · P(i))^{-β} / max_j(w_j)
```

`max_j(w_j)` normalises so the maximum weight is always 1.0, keeping gradient scales stable.

### β annealing

Early in training, bias is tolerable — IS correction can be weak. As training converges, unbiased gradients matter more. β is annealed linearly:

```python
β(t) = β_start + t / beta_anneal_steps × (1 − β_start)
```

Recommended: `β_start=0.4`, anneal to 1.0 over total training steps.

---

## Architecture

```
PrioritisedReplayBuffer
│
├── _SumTree (segment tree)
│   ├── O(log N) add / sample / update
│   ├── Leaf i stores priority p_i^α
│   └── Internal nodes store partial sums
│
├── IS correction weights
│   └── Computed on each sample() call
│
└── asyncio.Lock (single-process async safety)

Episode (frozen dataclass)
├── task_id: str
├── observations: NDArray[float32]   # shape (T, obs_dim)
├── actions: NDArray[float32]        # shape (T, act_dim)
├── rewards: NDArray[float32]        # shape (T,)
├── priority: float                  # initial |δ| + ε
└── timestamp: float                 # monotonic time at creation
```

---

## Types

### `Episode`

```python
@dataclass(frozen=True)
class Episode:
    task_id: str
    observations: npt.NDArray[np.float32]
    actions: npt.NDArray[np.float32]
    rewards: npt.NDArray[np.float32]
    priority: float = 1.0
    timestamp: float = field(default_factory=time.monotonic)
```

`frozen=True` makes `Episode` hashable and safe to store in sets/dicts.

### `ReplayBuffer` Protocol

```python
class ReplayBuffer(Protocol):
    async def add(self, episode: Episode) -> None: ...
    async def sample(
        self, n: int
    ) -> tuple[list[Episode], npt.NDArray[np.float64]]: ...
    async def update_priorities(
        self, task_ids: Sequence[str], new_priorities: npt.NDArray[np.float64]
    ) -> None: ...
    async def snapshot(self) -> ReplaySnapshot: ...
    async def restore(self, snap: ReplaySnapshot) -> None: ...
```

### `PrioritisedReplayBuffer`

```python
class PrioritisedReplayBuffer:
    def __init__(
        self,
        capacity: int = 10_000,
        alpha: float = 0.6,
        beta_start: float = 0.4,
        beta_anneal_steps: int = 100_000,
        epsilon: float = 1e-6,
    ) -> None:
        self._capacity = capacity
        self._alpha = alpha
        self._beta_start = beta_start
        self._beta_anneal_steps = beta_anneal_steps
        self._epsilon = epsilon
        self._sum_tree = _SumTree(capacity)
        self._lock = asyncio.Lock()
        self._step = 0
        self._total_added = 0
        self._total_sampled = 0

    @property
    def beta(self) -> float:
        t = min(self._step / self._beta_anneal_steps, 1.0)
        return self._beta_start + t * (1.0 - self._beta_start)

    async def add(self, episode: Episode) -> None:
        async with self._lock:
            priority = (episode.priority + self._epsilon) ** self._alpha
            self._sum_tree.add(priority, episode)
            self._total_added += 1
            _ADDED_TOTAL.inc()
            _REPLAY_SIZE.set(len(self._sum_tree))

    async def sample(
        self, n: int
    ) -> tuple[list[Episode], npt.NDArray[np.float64]]:
        async with self._lock:
            episodes, priorities = self._sum_tree.sample(n)
            total_p = self._sum_tree.total
            probs = priorities / total_p
            weights = (len(self._sum_tree) * probs) ** (-self.beta)
            weights /= weights.max()
            self._step += n
            self._total_sampled += n
            _SAMPLED_TOTAL.inc(n)
            return episodes, weights

    async def update_priorities(
        self, task_ids: Sequence[str], new_priorities: npt.NDArray[np.float64]
    ) -> None:
        async with self._lock:
            for task_id, p in zip(task_ids, new_priorities):
                idx = self._sum_tree.find_by_task_id(task_id)
                if idx is not None:
                    self._sum_tree.update(
                        idx, (float(p) + self._epsilon) ** self._alpha
                    )
        _MEAN_PRIORITY.set(float(new_priorities.mean()))
```

### `UniformReplayBuffer`

```python
from collections import deque

class UniformReplayBuffer:
    def __init__(self, capacity: int = 10_000) -> None:
        self._buffer: deque[Episode] = deque(maxlen=capacity)
        self._lock = asyncio.Lock()

    async def add(self, episode: Episode) -> None:
        async with self._lock:
            self._buffer.append(episode)
            _REPLAY_SIZE.set(len(self._buffer))
            _ADDED_TOTAL.inc()

    async def sample(
        self, n: int
    ) -> tuple[list[Episode], npt.NDArray[np.float64]]:
        async with self._lock:
            episodes = list(np.random.choice(
                list(self._buffer), size=min(n, len(self._buffer)), replace=False
            ))
            weights = np.ones(len(episodes), dtype=np.float64)
            _SAMPLED_TOTAL.inc(len(episodes))
            return episodes, weights
```

### `build_replay_buffer` factory

```python
def build_replay_buffer(
    strategy: str = "prioritised",
    capacity: int = 10_000,
    **kwargs,
) -> ReplayBuffer:
    match strategy:
        case "prioritised":
            return PrioritisedReplayBuffer(capacity=capacity, **kwargs)
        case "uniform":
            return UniformReplayBuffer(capacity=capacity)
        case _:
            raise ValueError(f"Unknown replay strategy: {strategy!r}")
```

---

## STDPOnlineLearner Integration

```python
class STDPOnlineLearner:
    def __init__(
        self,
        ...,
        replay_buffer: ReplayBuffer | None = None,
        replay_ratio: float = 0.25,
    ) -> None: ...

    async def update(self, obs, action, reward, ...) -> LearnerResult:
        # 1. Compute live STDP gradient Δw_live (existing logic)
        delta_live = await self._stdp_step(obs, action, reward)

        # 2. Sample replay episodes
        if self._replay_buffer is not None and len(self._replay_buffer) > 0:
            n_replay = max(1, int(self._replay_ratio * self._batch_size))
            replay_eps, is_weights = await self._replay_buffer.sample(n_replay)
            delta_replay = np.mean(
                [w * await self._stdp_step(e.observations, e.actions, e.rewards)
                 for e, w in zip(replay_eps, is_weights)],
                axis=0,
            )
            delta_live = (
                (1 - self._replay_ratio) * delta_live
                + self._replay_ratio * delta_replay
            )

        # 3. Add current episode to buffer
        if self._replay_buffer is not None:
            ep = Episode(
                task_id=self._current_task_id,
                observations=obs,
                actions=action,
                rewards=reward,
                priority=float(abs(delta_live).mean()),
            )
            asyncio.create_task(self._replay_buffer.add(ep))

        return self._apply_delta(delta_live)
```

---

## SLEEP_PHASE Hook Order (cumulative, Phase 7.3 adds step 8)

```
1.  STDPOnlineLearner.flush_pending_spikes()
2.  EWCRegulariser.consolidate(task_id)            # Phase 6.3
3.  FisherAccumulator.force_snapshot()              # Phase 6.4
4.  TaskRegistry.evict_if_needed()                  # Phase 6.5
5.  ReptileMetaLearner.meta_update()                # Phase 7.1
6.  CurriculumScheduler.advance_epoch()             # Phase 7.2
7.  TaskSampler.snapshot()                          # Phase 7.2
8.  PrioritisedReplayBuffer.snapshot()              # Phase 7.3  ← NEW
```

---

## _SumTree Implementation

The sum-tree is a segment tree where leaves store priorities and internal nodes store partial sums, enabling O(log N) updates and O(log N) weighted sampling.

```python
class _SumTree:
    """Segment tree for O(log N) priority operations."""

    def __init__(self, capacity: int) -> None:
        self._cap = capacity
        self._tree = np.zeros(2 * capacity, dtype=np.float64)
        self._episodes: list[Episode | None] = [None] * capacity
        self._task_to_idx: dict[str, int] = {}
        self._write = 0
        self._size = 0

    @property
    def total(self) -> float:
        return float(self._tree[1])

    def __len__(self) -> int:
        return self._size

    def add(self, priority: float, episode: Episode) -> None:
        idx = self._write
        self._episodes[idx] = episode
        self._task_to_idx[episode.task_id] = idx
        self._update_tree(idx + self._cap, priority)
        self._write = (self._write + 1) % self._cap
        self._size = min(self._size + 1, self._cap)

    def _update_tree(self, tree_idx: int, priority: float) -> None:
        self._tree[tree_idx] = priority
        tree_idx //= 2
        while tree_idx >= 1:
            self._tree[tree_idx] = (
                self._tree[2 * tree_idx] + self._tree[2 * tree_idx + 1]
            )
            tree_idx //= 2

    def _retrieve(self, idx: int, value: float) -> int:
        left = 2 * idx
        if left >= len(self._tree):
            return idx - self._cap
        if value <= self._tree[left]:
            return self._retrieve(left, value)
        return self._retrieve(left + 1, value - self._tree[left])

    def sample(self, n: int) -> tuple[list[Episode], npt.NDArray[np.float64]]:
        segments = np.linspace(0, self.total, n + 1)
        values = np.random.uniform(segments[:-1], segments[1:])
        indices = [self._retrieve(1, v) for v in values]
        priorities = np.array([self._tree[i + self._cap] for i in indices])
        episodes = [self._episodes[i] for i in indices]
        return episodes, priorities  # type: ignore[return-value]

    def update(self, leaf_idx: int, priority: float) -> None:
        self._update_tree(leaf_idx + self._cap, priority)

    def find_by_task_id(self, task_id: str) -> int | None:
        return self._task_to_idx.get(task_id)
```

---

## Prometheus Metrics

Declared at **module import** to avoid duplicate registration in tests:

```python
from prometheus_client import Counter, Gauge

_REPLAY_SIZE    = Gauge(
    "asi_replay_buffer_size", "Current number of stored episodes"
)
_REPLAY_CAP     = Gauge(
    "asi_replay_buffer_capacity", "Configured buffer capacity"
)
_ADDED_TOTAL    = Counter(
    "asi_replay_episodes_added_total", "Lifetime add() calls"
)
_SAMPLED_TOTAL  = Counter(
    "asi_replay_episodes_sampled_total", "Lifetime sample() calls"
)
_MEAN_PRIORITY  = Gauge(
    "asi_replay_mean_priority", "Rolling mean priority (EMA α=0.01)"
)
```

### PromQL monitoring

```promql
# Buffer fill percentage
asi_replay_buffer_size / asi_replay_buffer_capacity * 100

# Replay throughput (episodes/s)
rate(asi_replay_episodes_sampled_total[5m])

# Mean priority trend (rising = agent encountering harder tasks)
deriv(asi_replay_mean_priority[10m])

# Replay add/sample ratio (should be > 1 to keep buffer populated)
rate(asi_replay_episodes_added_total[1m]) /
  rate(asi_replay_episodes_sampled_total[1m])
```

---

## Test Targets (12)

| # | Test | Fixture |
|---|---|---|
| 1 | `test_add_increases_size` | Empty `PrioritisedReplayBuffer` |
| 2 | `test_capacity_evicts_lowest_priority` | Full buffer + high-priority episode |
| 3 | `test_sample_returns_n_episodes` | Buffer with 100 episodes |
| 4 | `test_sample_is_weights_max_is_one` | Verify `max(weights) == 1.0` |
| 5 | `test_update_priorities_changes_distribution` | Mock chi-square |
| 6 | `test_beta_annealing_increases_monotonically` | Steps 0, N/2, N |
| 7 | `test_uniform_buffer_fifo_eviction` | `UniformReplayBuffer` at capacity |
| 8 | `test_uniform_sample_uniform_distribution` | Chi-square p > 0.05 |
| 9 | `test_snapshot_restore_roundtrip` | `PrioritisedReplayBuffer` |
| 10 | `test_build_replay_buffer_factory` | Both strategy strings |
| 11 | `test_stdp_replay_ratio_blends_gradients` | `AsyncMock STDPOnlineLearner` |
| 12 | `test_prometheus_counters_increment` | `monkeypatch` Prometheus |

---

## Implementation Order

1. `Episode` dataclass (`frozen=True`, mypy annotations)
2. `ReplaySnapshot` dataclass (serialisable fields)
3. `_SumTree` segment tree (add, sample, update, find_by_task_id)
4. `PrioritisedReplayBuffer` (add, sample, update_priorities, snapshot/restore, β annealing)
5. `UniformReplayBuffer` (FIFO deque, uniform sample)
6. `build_replay_buffer()` factory (match statement)
7. Prometheus metrics (module-level declarations)
8. `STDPOnlineLearner` integration (`replay_buffer` kwarg, `replay_ratio`, gradient blend)
9. Unit tests (12 targets, `AsyncMock`, chi-square, `monkeypatch`)
10. mypy `--strict` pass

---

## Phase 7 Roadmap

| Sub-phase | Feature | Status |
|---|---|---|
| 7.1 | Reptile meta-learning ([Issue #259](https://github.com/web3guru888/asi-build/issues/259)) | 🟡 Open |
| 7.2 | Task sampler + curriculum ([Issue #262](https://github.com/web3guru888/asi-build/issues/262)) | 🟡 Open |
| **7.3** | **Episodic Replay Buffer ([Issue #265](https://github.com/web3guru888/asi-build/issues/265))** | **🟡 Open** |
| 7.4 | Hypernetwork context modulation | 📋 Planned |
| 7.5 | Phase 7 integration + benchmarks | 📋 Planned |
