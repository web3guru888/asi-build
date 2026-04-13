# Phase 13.3 — CuriosityModule (Intrinsic Motivation Engine)

**Phase**: 13 — World-Grounded Planning  
**Sub-phase**: 13.3  
**Issue**: [#374](https://github.com/web3guru888/asi-build/issues/374)  
**Depends on**: [WorldModel](Phase-13-World-Model) (#368), [DreamPlanner](Phase-13-Dream-Planner) (#371)  
**Discussions**: [Show & Tell #375](https://github.com/web3guru888/asi-build/discussions/375) · [Q&A #376](https://github.com/web3guru888/asi-build/discussions/376)

---

## Overview

`CuriosityModule` provides **intrinsic motivation** for the ASI-Build cognitive loop. It wraps `WorldModel.surprise()` and converts raw prediction error into a shaped **exploration bonus** blended with the extrinsic reward signal before any learning update. A running normaliser keeps bonuses stable regardless of how fast the world model improves.

---

## Enumerations

### `NormalisationStrategy`

```python
from enum import Enum, auto

class NormalisationStrategy(Enum):
    NONE       = auto()   # pass-through (ablations)
    RUNNING    = auto()   # divide by running std via Welford (default)
    PERCENTILE = auto()   # map to [0,1] via sliding-window percentile
    TANH       = auto()   # tanh squash
```

### `CuriosityDecaySchedule`

```python
class CuriosityDecaySchedule(Enum):
    CONSTANT    = auto()
    LINEAR      = auto()
    EXPONENTIAL = auto()   # default
    COSINE      = auto()
```

---

## Data classes (all `frozen=True`)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SurpriseEvent:
    step: int
    obs: tuple[float, ...]
    action: tuple[float, ...]
    raw_surprise: float           # MSE from WorldModel.surprise()
    normalised_surprise: float
    bonus: float                  # intrinsic_weight * normalised_surprise

@dataclass(frozen=True)
class CuriosityStats:
    running_mean: float
    running_std: float
    step_count: int
    intrinsic_weight: float       # current value after decay

@dataclass(frozen=True)
class CuriosityConfig:
    normalisation: NormalisationStrategy       = NormalisationStrategy.RUNNING
    decay_schedule: CuriosityDecaySchedule     = CuriosityDecaySchedule.EXPONENTIAL
    intrinsic_weight_init: float  = 0.1        # β₀
    intrinsic_weight_min:  float  = 0.001
    decay_rate: float             = 1e-5       # λ  (half-life ≈ ln(2)/λ steps)
    running_window: int           = 1_000      # for RUNNING normaliser warm-up
    percentile_window: int        = 10_000
    percentile_lo: float          = 5.0
    percentile_hi: float          = 95.0
    max_bonus: float              = 1.0        # hard cap
    enabled: bool                 = True
```

---

## `CuriosityModule` Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class CuriosityModule(Protocol):
    async def compute_bonus(
        self,
        obs: tuple[float, ...],
        action: tuple[float, ...],
        next_obs: tuple[float, ...],
        step: int,
    ) -> SurpriseEvent: ...

    async def batch_bonus(
        self,
        transitions: list[tuple[
            tuple[float, ...],   # obs
            tuple[float, ...],   # action
            tuple[float, ...],   # next_obs
        ]],
        step: int,
    ) -> list[SurpriseEvent]: ...

    def stats(self) -> CuriosityStats: ...
    def reset(self) -> None: ...
```

---

## `InMemoryCuriosityModule` — reference implementation

### Constructor

```python
class InMemoryCuriosityModule:
    def __init__(self, world_model: WorldModel, cfg: CuriosityConfig):
        self._wm   = world_model
        self._cfg  = cfg
        self._lock = asyncio.Lock()
        # Welford accumulators
        self._n    = 0
        self._mean = 0.0
        self._M2   = 0.0
        # percentile buffer
        self._pct_buf: deque[float] = deque(maxlen=cfg.percentile_window)
        # current intrinsic weight
        self._weight = cfg.intrinsic_weight_init
```

### Welford online statistics

```python
def _update_running(self, x: float) -> None:
    self._n += 1
    delta = x - self._mean
    self._mean += delta / self._n
    self._M2   += delta * (x - self._mean)

@property
def _running_std(self) -> float:
    if self._n < 2:
        return 1.0
    return math.sqrt(self._M2 / (self._n - 1)) + 1e-8
```

### Decay schedule

```python
def _decay_weight(self, step: int) -> float:
    β0, βmin, λ = (self._cfg.intrinsic_weight_init,
                   self._cfg.intrinsic_weight_min,
                   self._cfg.decay_rate)
    match self._cfg.decay_schedule:
        case CuriosityDecaySchedule.CONSTANT:
            return β0
        case CuriosityDecaySchedule.LINEAR:
            return max(βmin, β0 - λ * step)
        case CuriosityDecaySchedule.EXPONENTIAL:
            return max(βmin, β0 * math.exp(-λ * step))
        case CuriosityDecaySchedule.COSINE:
            T = max(1, int(1 / λ))
            t = min(step, T)
            return βmin + (β0 - βmin) * 0.5 * (1 + math.cos(math.pi * t / T))
        case _:
            return β0
```

### Normalisation

```python
def _normalise(self, raw: float) -> float:
    cfg = self._cfg
    match cfg.normalisation:
        case NormalisationStrategy.NONE:
            return raw
        case NormalisationStrategy.RUNNING:
            normed = (raw - self._mean) / self._running_std
            return max(0.0, normed)
        case NormalisationStrategy.PERCENTILE:
            buf = sorted(self._pct_buf) if self._pct_buf else [raw]
            lo  = buf[max(0, int(len(buf) * cfg.percentile_lo / 100))]
            hi  = buf[min(len(buf)-1, int(len(buf) * cfg.percentile_hi / 100))]
            if hi == lo:
                return 0.5
            return max(0.0, min(1.0, (raw - lo) / (hi - lo)))
        case NormalisationStrategy.TANH:
            return float(math.tanh(raw / (self._running_std + 1e-8)))
        case _:
            return raw
```

### `compute_bonus()`

```python
async def compute_bonus(self, obs, action, next_obs, step) -> SurpriseEvent:
    if not self._cfg.enabled:
        return SurpriseEvent(step=step, obs=obs, action=action,
                             raw_surprise=0.0, normalised_surprise=0.0, bonus=0.0)

    raw = await self._wm.surprise(obs, action, next_obs)

    async with self._lock:
        self._update_running(raw)
        self._pct_buf.append(raw)
        normed = self._normalise(raw)
        weight = self._decay_weight(step)
        self._weight = weight

    bonus = min(self._cfg.max_bonus, weight * normed)

    _curiosity_bonus.observe(bonus)
    _curiosity_raw_surprise.observe(raw)
    _curiosity_weight.set(weight)

    return SurpriseEvent(step=step, obs=obs, action=action,
                         raw_surprise=raw, normalised_surprise=normed, bonus=bonus)
```

### `batch_bonus()`

```python
async def batch_bonus(self, transitions, step) -> list[SurpriseEvent]:
    coros = [self.compute_bonus(obs, act, nxt, step)
             for obs, act, nxt in transitions]
    results = list(await asyncio.gather(*coros))
    _curiosity_batch_size.observe(len(results))
    return results
```

### `stats()` and `reset()`

```python
def stats(self) -> CuriosityStats:
    return CuriosityStats(
        running_mean=self._mean,
        running_std=self._running_std,
        step_count=self._n,
        intrinsic_weight=self._weight,
    )

def reset(self) -> None:
    self._n = 0
    self._mean = self._M2 = 0.0
    self._pct_buf.clear()
    self._weight = self._cfg.intrinsic_weight_init
    _curiosity_resets.inc()
```

---

## Factory

```python
def build_curiosity_module(
    world_model: WorldModel,
    cfg: CuriosityConfig | None = None,
) -> CuriosityModule:
    return InMemoryCuriosityModule(world_model, cfg or CuriosityConfig())
```

---

## `CognitiveCycle` integration

```python
class CognitiveCycle:
    # existing fields …
    _curiosity: CuriosityModule

    async def _step(
        self,
        obs: tuple[float, ...],
        action: tuple[float, ...],
        next_obs: tuple[float, ...],
        extrinsic_reward: float,
        step: int,
    ) -> float:
        """Return blended reward = extrinsic + intrinsic bonus."""
        event = await self._curiosity.compute_bonus(obs, action, next_obs, step)
        blended = extrinsic_reward + event.bonus
        _curiosity_blended_reward.observe(blended)
        return blended
```

---

## Normalisation strategy guide

| Strategy | When to use | Key config |
|----------|-------------|-----------|
| `RUNNING` | General default; adapts as WM improves | — |
| `PERCENTILE` | Heavy-tailed surprise distributions | `percentile_lo`, `percentile_hi` |
| `TANH` | Policy-gradient methods; smooth gradient | — |
| `NONE` | Ablation; pre-normalised externally | — |

## Decay schedule guide

| Schedule | Formula | Half-life (λ=1e-5) |
|----------|---------|---------------------|
| `EXPONENTIAL` | `β₀ · e^(−λt)` | ~69k steps |
| `LINEAR` | `max(βmin, β₀ − λt)` | ~10k steps |
| `COSINE` | cosine from β₀→βmin over T=1/λ steps | smooth |
| `CONSTANT` | `β₀` | never (debug) |

---

## Prometheus metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_curiosity_bonus` | Histogram | Intrinsic bonus per transition |
| `asi_curiosity_raw_surprise` | Histogram | Raw WorldModel MSE |
| `asi_curiosity_weight` | Gauge | Current intrinsic weight β |
| `asi_curiosity_resets_total` | Counter | Module resets |
| `asi_curiosity_batch_size` | Histogram | Batch sizes via `batch_bonus` |

```python
from prometheus_client import Counter, Gauge, Histogram

_curiosity_bonus        = Histogram("asi_curiosity_bonus", "Intrinsic bonus per step",
                                    buckets=[0,.01,.05,.1,.25,.5,1.])
_curiosity_raw_surprise = Histogram("asi_curiosity_raw_surprise", "Raw WorldModel MSE",
                                    buckets=[0,.001,.01,.1,1.,10.])
_curiosity_weight       = Gauge("asi_curiosity_weight", "Current intrinsic weight β")
_curiosity_resets       = Counter("asi_curiosity_resets_total", "Module resets")
_curiosity_batch_size   = Histogram("asi_curiosity_batch_size", "batch_bonus sizes",
                                    buckets=[1,2,4,8,16,32,64,128])
```

### PromQL examples

```promql
# 95th-percentile bonus
histogram_quantile(0.95, rate(asi_curiosity_bonus_bucket[5m]))

# curiosity weight decay trend
asi_curiosity_weight

# alert: weight stuck (decay not working)
ALERT CuriosityWeightStuck
  IF asi_curiosity_weight > 0.09
  FOR 10m
  LABELS { severity="warning" }
  ANNOTATIONS { summary="CuriosityModule: weight not decaying — check decay_rate" }
```

---

## mypy compatibility

| Symbol | Notes |
|--------|-------|
| `NormalisationStrategy` | `Enum` — no issues |
| `CuriosityDecaySchedule` | `Enum` — no issues |
| `SurpriseEvent` | `@dataclass(frozen=True)` — all fields typed |
| `CuriosityStats` | `@dataclass(frozen=True)` — all fields typed |
| `CuriosityConfig` | `@dataclass(frozen=True)` — all fields typed |
| `CuriosityModule` | `@runtime_checkable Protocol` |
| `InMemoryCuriosityModule` | satisfies Protocol; `deque[float]` typed |
| `_running_std` | `@property` returns `float` |

---

## Test targets (12)

1. `test_curiosity_compute_bonus_returns_surprise_event`
2. `test_curiosity_bonus_non_negative`
3. `test_curiosity_bonus_capped_at_max`
4. `test_running_normalisation_stable_after_warmup`
5. `test_percentile_normalisation_range`
6. `test_tanh_normalisation_output_bounded`
7. `test_none_normalisation_passthrough`
8. `test_exponential_decay_decreases_weight`
9. `test_linear_decay_floored_at_min`
10. `test_cosine_decay_smooth`
11. `test_batch_bonus_asyncio_gather`
12. `test_reset_clears_running_stats`

---

## Implementation order (14 steps)

1. Add `NormalisationStrategy` and `CuriosityDecaySchedule` enums
2. Add `SurpriseEvent`, `CuriosityStats`, `CuriosityConfig` dataclasses
3. Define `CuriosityModule` Protocol
4. Implement `_update_running()` + `_running_std` (Welford online)
5. Implement `_decay_weight()` for all 4 schedules
6. Implement `_normalise()` for all 4 strategies
7. Implement `compute_bonus()` with Prometheus emit
8. Implement `batch_bonus()` via `asyncio.gather`
9. Implement `stats()` and `reset()`
10. Wire `build_curiosity_module()` factory
11. Add `CognitiveCycle._step()` blended-reward integration
12. Add Prometheus metric declarations
13. Write 12 unit tests (mock WorldModel)
14. Extend mypy config and CI matrix

---

## Phase 13 roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 13.1 | WorldModel | [#368](https://github.com/web3guru888/asi-build/issues/368) | 🟡 In Progress |
| 13.2 | DreamPlanner | [#371](https://github.com/web3guru888/asi-build/issues/371) | 🟡 In Progress |
| 13.3 | CuriosityModule | [#374](https://github.com/web3guru888/asi-build/issues/374) | 🟡 In Progress |
| 13.4 | LatentSpaceNavigator | TBD | ⏳ Planned |
| 13.5 | Phase 13 Wiring + Phase 14 Planning | TBD | ⏳ Planned |

## Phase 12 recap

| Sub-phase | Component | Issue |
|-----------|-----------|-------|
| 12.1 | AgentRegistry | [#352](https://github.com/web3guru888/asi-build/issues/352) |
| 12.2 | NegotiationEngine | [#355](https://github.com/web3guru888/asi-build/issues/355) |
| 12.3 | CollaborationChannel | [#358](https://github.com/web3guru888/asi-build/issues/358) |
| 12.4 | ConsensusVoting | [#361](https://github.com/web3guru888/asi-build/issues/361) |
| 12.5 | CoalitionFormation | [#364](https://github.com/web3guru888/asi-build/issues/364) |
