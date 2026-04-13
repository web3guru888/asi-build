# Phase 13.2 — `DreamPlanner`: Model-Predictive Planning in Imagination Space

> **Phase 13 — World Modeling & Model-Based Planning**  
> **Sub-phase 13.2** | Depends on: Phase 13.1 `WorldModel` (#368) | Issue: #371  
> Show & Tell: #372 | Q&A: #373

---

## Overview

`DreamPlanner` is the model-predictive control (MPC) layer for ASI:BUILD. It evaluates many candidate action sequences *in imagination* using `WorldModel.dream_rollout()` and `WorldModel.predict()`, then selects the action with the best predicted discounted return — without executing a single real action.

This separates **planning** (deciding what to do) from **acting** (doing it), enabling lookahead reasoning grounded in the agent's internal world model.

---

## Enums

```python
class PlanningStrategy(str, Enum):
    RANDOM_SHOOTING = "random_shooting"  # sample N random sequences, pick best
    CEM             = "cem"              # Cross-Entropy Method iterative refinement
    BEAM_SEARCH     = "beam_search"      # deterministic tree expansion, top-K pruning
    GREEDY          = "greedy"           # single rollout, argmax reward (baseline)

class PlanOutcome(str, Enum):
    SUCCESS         = "success"          # plan found within horizon
    HORIZON_BREACH  = "horizon_breach"   # no done within H steps
    NO_CANDIDATES   = "no_candidates"    # zero valid action sequences generated
    SURPRISE_ABORT  = "surprise_abort"   # world model surprise too high mid-plan
```

---

## Core Dataclasses (all `frozen=True`)

```python
@dataclass(frozen=True)
class ActionCandidate:
    action_sequence: tuple[int, ...]   # length == horizon
    predicted_reward: float
    terminal_surprise: float           # surprise() at final imagined obs
    rollout_steps: int                 # actual steps before done

@dataclass(frozen=True)
class PlanResult:
    outcome: PlanOutcome
    best_action: int                   # first action to take
    best_sequence: tuple[int, ...]
    predicted_reward: float
    candidates_evaluated: int
    planning_time_ms: float

@dataclass(frozen=True)
class DreamPlannerConfig:
    strategy: PlanningStrategy = PlanningStrategy.RANDOM_SHOOTING
    horizon: int = 10                  # H — planning horizon (steps)
    n_candidates: int = 64            # N — candidate sequences for RANDOM_SHOOTING/CEM
    cem_iterations: int = 3           # CEM refinement rounds
    cem_elite_frac: float = 0.2       # fraction of elite samples kept per CEM round
    beam_width: int = 8               # top-K beams for BEAM_SEARCH
    action_dim: int = 4               # discrete action space size
    surprise_abort_threshold: float = 2.0  # abort plan if surprise > this
    discount: float = 0.99            # reward discounting
    max_planning_ms: float = 50.0     # wall-clock budget
```

---

## Protocol

```python
class DreamPlanner(Protocol):
    async def plan(
        self,
        initial_obs: np.ndarray,
        world_model: WorldModel,
    ) -> PlanResult: ...

    async def plan_batch(
        self,
        obs_batch: list[np.ndarray],
        world_model: WorldModel,
    ) -> list[PlanResult]: ...

    @property
    def config(self) -> DreamPlannerConfig: ...
```

---

## `InMemoryDreamPlanner` — Reference Implementation

### `__init__` + helpers

```python
class InMemoryDreamPlanner:
    def __init__(self, cfg: DreamPlannerConfig) -> None:
        self._cfg = cfg
        self._rng = np.random.default_rng()

    def _discounted_return(self, rollout: DreamRollout) -> float:
        total = 0.0
        for i, r in enumerate(rollout.rewards):
            total += (self._cfg.discount ** i) * r
        return total

    def _select_best(self, candidates: list[ActionCandidate], t0: float) -> PlanResult:
        if not candidates:
            return PlanResult(
                outcome=PlanOutcome.NO_CANDIDATES,
                best_action=0, best_sequence=(),
                predicted_reward=0.0, candidates_evaluated=0,
                planning_time_ms=(time.monotonic() - t0) * 1000,
            )
        best = max(candidates, key=lambda c: c.predicted_reward)
        return PlanResult(
            outcome=PlanOutcome.SUCCESS,
            best_action=best.action_sequence[0],
            best_sequence=best.action_sequence,
            predicted_reward=best.predicted_reward,
            candidates_evaluated=len(candidates),
            planning_time_ms=(time.monotonic() - t0) * 1000,
        )
```

### `_random_shooting`

```python
async def _random_shooting(self, obs, wm, t0) -> PlanResult:
    candidates: list[ActionCandidate] = []
    for _ in range(self._cfg.n_candidates):
        if (time.monotonic() - t0) * 1000 > self._cfg.max_planning_ms:
            break
        seq = tuple(self._rng.integers(0, self._cfg.action_dim, self._cfg.horizon).tolist())
        rollout = await wm.dream_rollout(ModelInput(obs=obs, action=seq[0]), horizon=self._cfg.horizon)
        total_r = self._discounted_return(rollout)
        terminal_surprise = float(np.mean(rollout.surprises)) if rollout.surprises else 0.0
        if terminal_surprise > self._cfg.surprise_abort_threshold:
            _PLAN_SURPRISE_ABORT.inc()
            continue  # world model uncertain — discard
        candidates.append(ActionCandidate(seq, total_r, terminal_surprise, len(rollout.observations)))
    return self._select_best(candidates, t0)
```

### `_cem` (Cross-Entropy Method)

```python
async def _cem(self, obs, wm, t0) -> PlanResult:
    H, N = self._cfg.horizon, self._cfg.n_candidates
    n_elite = max(1, int(N * self._cfg.cem_elite_frac))
    mean = np.ones((H, self._cfg.action_dim)) / self._cfg.action_dim
    candidates: list[ActionCandidate] = []
    for _ in range(self._cfg.cem_iterations):
        if (time.monotonic() - t0) * 1000 > self._cfg.max_planning_ms:
            break
        batch_cands: list[ActionCandidate] = []
        for _ in range(N):
            seq = tuple(np.argmax(
                mean + self._rng.standard_normal((H, self._cfg.action_dim)) * 0.5, axis=-1
            ).tolist())
            rollout = await wm.dream_rollout(ModelInput(obs=obs, action=seq[0]), horizon=H)
            total_r = self._discounted_return(rollout)
            batch_cands.append(ActionCandidate(seq, total_r, 0.0, len(rollout.observations)))
        elite = sorted(batch_cands, key=lambda c: c.predicted_reward, reverse=True)[:n_elite]
        candidates.extend(elite)
        elite_seqs = np.array([list(e.action_sequence) for e in elite])
        for h in range(H):
            counts = np.bincount(elite_seqs[:, h], minlength=self._cfg.action_dim)
            mean[h] = counts / counts.sum()
        # Early convergence exit
        entropy = -np.sum(mean * np.log(mean + 1e-8), axis=-1).mean()
        if entropy < 0.01:
            break
    return self._select_best(candidates, t0)
```

### `_beam_search`

```python
async def _beam_search(self, obs, wm, t0) -> PlanResult:
    beams: list[tuple[float, np.ndarray, tuple[int, ...]]] = [(0.0, obs, ())]
    for step in range(self._cfg.horizon):
        if (time.monotonic() - t0) * 1000 > self._cfg.max_planning_ms:
            break
        next_beams: list[tuple[float, np.ndarray, tuple[int, ...]]] = []
        for cum_r, cur_obs, seq in beams:
            for a in range(self._cfg.action_dim):
                out = await wm.predict(ModelInput(obs=cur_obs, action=a))
                new_r = cum_r + (self._cfg.discount ** step) * out.reward
                next_beams.append((new_r, out.next_obs, seq + (a,)))
        next_beams.sort(key=lambda x: x[0], reverse=True)
        beams = next_beams[: self._cfg.beam_width]
    candidates = [
        ActionCandidate(seq, r, 0.0, self._cfg.horizon)
        for r, _, seq in beams
    ]
    return self._select_best(candidates, t0)
```

### `plan` dispatcher + `plan_batch`

```python
async def plan(self, initial_obs: np.ndarray, world_model: WorldModel) -> PlanResult:
    t0 = time.monotonic()
    strategy_map = {
        PlanningStrategy.RANDOM_SHOOTING: self._random_shooting,
        PlanningStrategy.CEM:            self._cem,
        PlanningStrategy.BEAM_SEARCH:    self._beam_search,
        PlanningStrategy.GREEDY:         self._greedy,
    }
    result = await strategy_map[self._cfg.strategy](initial_obs, world_model, t0)
    _PLAN_LATENCY.labels(strategy=self._cfg.strategy.value).observe(
        (time.monotonic() - t0) * 1000
    )
    _PLAN_OUTCOME.labels(outcome=result.outcome.value).inc()
    _PLAN_PREDICTED_REWARD.labels(strategy=self._cfg.strategy.value).set(result.predicted_reward)
    _PLAN_CANDIDATES.labels(strategy=self._cfg.strategy.value).inc(result.candidates_evaluated)
    return result

async def plan_batch(
    self,
    obs_batch: list[np.ndarray],
    world_model: WorldModel,
) -> list[PlanResult]:
    tasks = [self.plan(obs, world_model) for obs in obs_batch]
    return list(await asyncio.gather(*tasks))
```

---

## Factory

```python
def build_dream_planner(cfg: DreamPlannerConfig | None = None) -> DreamPlanner:
    return InMemoryDreamPlanner(cfg or DreamPlannerConfig())
```

---

## `CognitiveCycle` Integration

```python
class CognitiveCycle:
    _dream_planner: DreamPlanner
    _world_model: WorldModel

    async def _model_based_step(self, obs: np.ndarray) -> int:
        """Return best action from DreamPlanner; fallback to 0 on error."""
        try:
            result: PlanResult = await self._dream_planner.plan(obs, self._world_model)
            if result.outcome == PlanOutcome.SUCCESS:
                _PLAN_SUCCESS.inc()
                return result.best_action
            _PLAN_FALLBACK.inc()
        except Exception:
            _PLAN_ERROR.inc()
        return 0  # safe default
```

---

## Planning Strategy Decision Guide

| Scenario | Strategy | `n_candidates` | `horizon` | Notes |
|----------|----------|---------------|-----------|-------|
| Real-time control (< 50ms) | `RANDOM_SHOOTING` | 16–32 | 5–8 | Sub-ms per sample |
| Best quality (offline/batch) | `CEM` | 64–128 | 10–20 | 3 iterations typical |
| Deterministic discrete env | `BEAM_SEARCH` | — | 6–12 | `beam_width` 4–16 |
| Debug / ablation | `GREEDY` | 1 | any | Minimal WM calls |

---

## Dream Rollout State Machine

```
start ──► _random_shooting/CEM/BEAM_SEARCH/GREEDY
              │
              ▼
         candidate evaluated
              │
         terminal_surprise > threshold?
              ├── yes ──► discard, SURPRISE_ABORT++
              └── no  ──► append to candidates
              │
         time budget exceeded?
              ├── yes ──► break loop
              └── no  ──► next candidate
              │
         _select_best(candidates)
              │
         candidates empty? ──► PlanOutcome.NO_CANDIDATES
              │
         return PlanResult.SUCCESS (best_action)
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_dream_plan_latency_ms` | Histogram | `strategy` | Wall-clock planning time per call |
| `asi_dream_plan_candidates_total` | Counter | `strategy` | Cumulative candidates evaluated |
| `asi_dream_plan_outcome_total` | Counter | `outcome` | SUCCESS / HORIZON_BREACH / NO_CANDIDATES / SURPRISE_ABORT |
| `asi_dream_plan_predicted_reward` | Gauge | `strategy` | Best predicted reward from last plan |
| `asi_dream_plan_surprise_abort_total` | Counter | — | Plans aborted due to high world-model surprise |

### PromQL

```promql
# Planning success rate
rate(asi_dream_plan_outcome_total{outcome="success"}[5m])
/ rate(asi_dream_plan_outcome_total[5m])

# 99th-percentile latency per strategy
histogram_quantile(0.99, rate(asi_dream_plan_latency_ms_bucket[5m]))
```

### Grafana Alert YAML

```yaml
- alert: DreamPlannerHighLatency
  expr: histogram_quantile(0.99, rate(asi_dream_plan_latency_ms_bucket[5m])) > 45
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "DreamPlanner 99th-pct latency > 45ms (budget 50ms)"

- alert: DreamPlannerLowSuccessRate
  expr: |
    rate(asi_dream_plan_outcome_total{outcome="success"}[5m])
    / rate(asi_dream_plan_outcome_total[5m]) < 0.8
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "DreamPlanner success rate < 80%"
```

---

## `mypy --strict` Compliance

| Symbol | Type notes |
|--------|------------|
| `ActionCandidate` | `frozen=True` dataclass, `action_sequence: tuple[int, ...]` |
| `PlanResult` | `frozen=True` dataclass, `best_sequence: tuple[int, ...]` |
| `DreamPlannerConfig` | `frozen=True` dataclass, all fields typed |
| `InMemoryDreamPlanner.plan` | `async def plan(self, obs: np.ndarray, wm: WorldModel) -> PlanResult` |
| `_random_shooting` | `-> PlanResult` |
| `_cem` | `mean: np.ndarray` shape `(H, action_dim)` |
| `_beam_search` | `beams: list[tuple[float, np.ndarray, tuple[int, ...]]]` |
| `plan_batch` | `obs_batch: list[np.ndarray]` → `list[PlanResult]` |

---

## Test Targets (12)

| # | Test | Focus |
|---|------|-------|
| 1 | `test_random_shooting_returns_plan_result` | N=4, H=3, verifies `SUCCESS` |
| 2 | `test_cem_refines_reward_over_iterations` | Reward improves across CEM rounds |
| 3 | `test_beam_search_expands_action_dim_wide` | Beam width respected, best beam selected |
| 4 | `test_greedy_single_rollout` | `dream_rollout` called exactly once |
| 5 | `test_no_candidates_outcome` | All candidates aborted → `NO_CANDIDATES` |
| 6 | `test_time_budget_respected` | Wall-clock < `max_planning_ms` + 5ms slack |
| 7 | `test_discount_applied_correctly` | 2-step rollout, r=[1,1], γ=0.5 → 1.5 |
| 8 | `test_surprise_abort_threshold` | High surprise → candidates discarded |
| 9 | `test_plan_batch_parallel` | 4 obs → 4 PlanResults via `asyncio.gather` |
| 10 | `test_cem_elite_fraction_shrinks_entropy` | Elite mean converges toward optimal action |
| 11 | `test_config_defaults` | `DreamPlannerConfig()` matches spec defaults |
| 12 | `test_cognitive_cycle_uses_dream_planner` | `_model_based_step` delegates to planner |

---

## Implementation Order (14 steps)

1. Define `PlanningStrategy` and `PlanOutcome` enums in `enums.py`
2. Define `ActionCandidate`, `PlanResult`, `DreamPlannerConfig` frozen dataclasses
3. Define `DreamPlanner` Protocol
4. Implement `InMemoryDreamPlanner.__init__` + `_select_best` + `_discounted_return`
5. Implement `_greedy` using `WorldModel.dream_rollout()`
6. Implement `_random_shooting` with time-budget + surprise-abort guards
7. Implement `_cem` with `cem_iterations` + elite re-fit + entropy-convergence exit
8. Implement `_beam_search` with `WorldModel.predict()` per node
9. Implement `plan_batch()` with `asyncio.gather()`
10. Wire `CognitiveCycle._model_based_step()` to call `DreamPlanner.plan()`
11. Add 5 Prometheus metrics
12. Add `build_dream_planner()` factory
13. Write 12 tests (`pytest-asyncio`, mock `WorldModel`)
14. Run `mypy --strict` + `pytest -x`

---

## Phase 13 Roadmap

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 13.1 | `WorldModel` | #368 | 🟡 in progress |
| **13.2** | **`DreamPlanner`** | **#371** | **🟡 this page** |
| 13.3 | `CuriosityEngine` | ⏳ | planned |
| 13.4 | `LatentStateEncoder` | ⏳ | planned |
| 13.5 | `ModelEnsembleCoordinator` | ⏳ | planned |

---

## Phase 12 Recap

Phase 12 (Distributed Coordination & Multi-Agent Collaboration) is complete — all 5 sub-phases spec'd:

| Sub-phase | Component | Issue |
|-----------|-----------|-------|
| 12.1 | `AgentRegistry` | #352 |
| 12.2 | `NegotiationEngine` | #355 |
| 12.3 | `CollaborationChannel` | #358 |
| 12.4 | `ConsensusVoting` | #361 |
| 12.5 | `CoalitionFormation` | #364 |

---

*Part of the ASI:BUILD Roadmap — Phase 13: World Modeling & Model-Based Planning*
