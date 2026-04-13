# Phase 13.1 — WorldModel

**Component**: `WorldModel`
**Phase**: 13.1 (World Modeling & Model-Based Planning)
**Issue**: [#368](https://github.com/web3guru888/asi-build/issues/368)
**Discussions**: [Show & Tell #369](https://github.com/web3guru888/asi-build/discussions/369) | [Q&A #370](https://github.com/web3guru888/asi-build/discussions/370)
**Status**: 🟡 In progress

---

## Overview

`WorldModel` is a predictive model of environment dynamics. It enables model-based planning: instead of relying solely on trial-and-error, the agent simulates imagined trajectories through its internal model, selects the best action sequence, and executes with far greater sample efficiency.

### Key capabilities

- **One-step prediction** — given (obs, action), predict next_obs + reward + done
- **Dream rollouts** — simulate H-step trajectories in imagination
- **Surprise detection** — high prediction error flags distributional shift → triggers replanning
- **Online learning** — continuously update from real transitions via SGD + replay buffer
- **Epistemic uncertainty** — ENSEMBLE backend tracks inter-model variance for exploration

---

## Enumerations

```python
from enum import Enum, auto

class TransitionBackend(Enum):
    """Neural architecture for the world model forward pass."""
    MLP         = auto()  # feed-forward, ~0.1ms, low capacity
    LSTM        = auto()  # recurrent, ~0.5ms, temporal context
    TRANSFORMER = auto()  # attention, ~2ms, long histories
    ENSEMBLE    = auto()  # N×MLP, epistemic uncertainty

class PredictionTarget(Enum):
    """What the model predicts."""
    NEXT_OBS = auto()  # next observation vector
    REWARD   = auto()  # scalar reward
    DONE     = auto()  # episode termination flag
    ALL      = auto()  # joint head (obs + reward + done)
```

---

## Data Classes

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelInput:
    observation: tuple[float, ...]  # current obs vector
    action: int                     # discrete action index

@dataclass(frozen=True)
class ModelOutput:
    next_observation: tuple[float, ...]  # predicted next obs
    predicted_reward: float              # predicted reward
    predicted_done: bool                 # predicted termination
    prediction_error: float              # MSE vs last ground-truth

@dataclass(frozen=True)
class DreamRollout:
    steps: tuple[ModelOutput, ...]  # ordered imagined steps
    total_imagined_reward: float    # sum of predicted rewards
    surprise_score: float           # mean prediction_error

@dataclass(frozen=True)
class WorldModelConfig:
    backend: TransitionBackend = TransitionBackend.MLP
    obs_dim: int = 64
    action_dim: int = 8
    hidden_dim: int = 256
    ensemble_size: int = 5
    rollout_horizon: int = 10
    learning_rate: float = 3e-4
    surprise_threshold: float = 0.05
    max_buffer_size: int = 100_000
```

---

## Protocol

```python
from typing import Protocol, Sequence, runtime_checkable

@runtime_checkable
class WorldModel(Protocol):
    async def predict(self, inp: ModelInput) -> ModelOutput: ...
    async def dream_rollout(
        self,
        initial_obs: tuple[float, ...],
        action_sequence: Sequence[int],
    ) -> DreamRollout: ...
    async def update(
        self,
        inp: ModelInput,
        actual_next_obs: tuple[float, ...],
        actual_reward: float,
        actual_done: bool,
    ) -> float: ...
    async def surprise(
        self,
        inp: ModelInput,
        actual_next_obs: tuple[float, ...],
    ) -> float: ...
    async def snapshot(self) -> dict: ...
```

---

## `InMemoryWorldModel`

### `__init__()`
- `asyncio.Lock` for all forward passes and weight updates
- `deque(maxlen=max_buffer_size)` replay buffer
- `_step_count: int` for snapshot reporting

### `_forward(inp: ModelInput) → ModelOutput`
Stub implementation: perturbs current obs by small Gaussian noise.  
**Key**: always pad/truncate to `obs_dim` before returning.  
Replace with real `torch.nn.Module` forward pass in production.

### `predict(inp)`
Acquires `_lock`, calls `_forward()`, returns `ModelOutput`.

### `update(inp, actual_next_obs, reward, done)`
1. Appends transition to replay buffer
2. Calls `_sgd_step()` — returns scalar loss
3. Increments `_step_count`, updates metrics
4. Returns loss

### `_sgd_step(inp, actual_next_obs, reward, done)`
Stub: computes MSE(predicted_obs, actual_obs), sets `_wm_train_loss`.  
Replace with autograd optimizer step in production.

### `dream_rollout(initial_obs, action_sequence)`
Holds `_lock` for entire trajectory to prevent mid-rollout weight updates:
```python
obs = initial_obs
steps = []
for action in action_sequence:
    out = await self._forward(ModelInput(observation=obs, action=action))
    steps.append(out)
    _wm_rollout_steps_total.inc()
    if out.predicted_done:
        break  # early exit
    obs = out.next_observation
total_reward = sum(s.predicted_reward for s in steps)
surprise = sum(s.prediction_error for s in steps) / max(len(steps), 1)
return DreamRollout(tuple(steps), total_reward, surprise)
```

### `surprise(inp, actual_next_obs)`
```python
out = await self.predict(inp)
err = _mse(out.next_observation, actual_next_obs)
_wm_surprise_score.set(err)
return err
```

### `snapshot()`
Returns `{"config": ..., "step_count": ..., "buffer_size": ...}`.

---

## Factory

```python
def build_world_model(config: WorldModelConfig | None = None) -> WorldModel:
    return InMemoryWorldModel(config or WorldModelConfig())
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    def __init__(self, ..., world_model: WorldModel) -> None:
        self._world_model = world_model

    async def _model_based_step(
        self,
        obs: tuple[float, ...],
        candidate_actions: list[int],
    ) -> int:
        best_action, best_reward = candidate_actions[0], float("-inf")
        for action in candidate_actions:
            rollout = await self._world_model.dream_rollout(
                initial_obs=obs,
                action_sequence=[action] * self._cfg.rollout_horizon,
            )
            if rollout.total_imagined_reward > best_reward:
                best_reward = rollout.total_imagined_reward
                best_action = action
            if rollout.surprise_score > self._cfg.wm.surprise_threshold:
                await self._trigger_replan()
        return best_action

    async def _update_world_model(
        self,
        inp: ModelInput,
        actual_next_obs: tuple[float, ...],
        actual_reward: float,
        actual_done: bool,
    ) -> None:
        loss = await self._world_model.update(inp, actual_next_obs, actual_reward, actual_done)
        _wm_train_loss.set(loss)
```

---

## Dream Rollout — State Machine

```
obs₀ ──► _forward(obs₀, a₀) ──► ModelOutput₀
          └── next_obs₁, r₀, done₀=False ──► continue
obs₁ ──► _forward(obs₁, a₁) ──► ModelOutput₁
          └── next_obs₂, r₁, done₁=True  ──► BREAK (early exit)

DreamRollout assembled:
  steps = (Output₀, Output₁)
  total_imagined_reward = r₀ + r₁
  surprise_score = mean(error₀, error₁)
```

---

## TransitionBackend Selection Guide

| Backend | Latency | Capacity | When to use |
|---------|---------|----------|-------------|
| `MLP` | ~0.1ms | Low | Short-horizon tasks, fast iteration |
| `LSTM` | ~0.5ms | Medium | Temporal dependencies, POMDPs |
| `TRANSFORMER` | ~2ms | High | Long observation histories (>50 steps) |
| `ENSEMBLE` | ~N×MLP | High + uncertainty | Exploration-heavy, high-stakes decisions |

### ENSEMBLE — epistemic uncertainty

```python
# All N members predict
predictions = [await m.predict(inp) for m in self._ensemble]
# Mean = best estimate
mean_obs = tuple(
    sum(p.next_observation[i] for p in predictions) / len(predictions)
    for i in range(self._cfg.obs_dim)
)
# Variance = epistemic uncertainty (use as exploration bonus)
variance = sum(_mse(p.next_observation, mean_obs) for p in predictions) / len(predictions)
```

---

## Prometheus Metrics

```python
from prometheus_client import Counter, Gauge

_wm_update_total        = Counter("wm_update_total",        "Real transitions consumed")
_wm_train_loss          = Gauge("wm_train_loss",            "Most recent SGD loss")
_wm_surprise_score      = Gauge("wm_surprise_score",        "Most recent surprise score")
_wm_buffer_size         = Gauge("wm_buffer_size",           "Replay buffer fill level")
_wm_rollout_steps_total = Counter("wm_rollout_steps_total", "Dream rollout steps executed")
```

**PromQL examples:**
```promql
# Surprise spikes — distribution shift
wm_surprise_score > 0.05

# Model update rate (transitions/min)
rate(wm_update_total[1m])

# Training convergence
wm_train_loss
```

**Grafana alert:**
```yaml
- alert: WorldModelSurpriseSpike
  expr: wm_surprise_score > 0.1
  for: 2m
  labels: { severity: warning }
  annotations:
    summary: "WorldModel surprise > 0.1 for 2m — possible distribution shift"
```

---

## mypy Compliance

| Class/Function | Issue | Resolution |
|----------------|-------|------------|
| `ModelInput.observation` | `tuple[float, ...]` vs `list` | wrap in `tuple()` at call boundary |
| `DreamRollout.steps` | built as list internally | `tuple(steps)` before freeze |
| `_forward()` obs length | must equal `obs_dim` | pad with zeros, truncate to `obs_dim` |
| `build_world_model` return | `WorldModel` Protocol | `# type: ignore[return-value]` if needed |

---

## Test Targets (12 minimum)

1. `test_predict_returns_model_output` — output type + field types
2. `test_predict_obs_dim_preserved` — `len(next_obs) == obs_dim`
3. `test_dream_rollout_length` — `1 <= len(steps) <= horizon`
4. `test_dream_rollout_terminates_on_done` — early exit when `predicted_done=True`
5. `test_update_returns_scalar_loss` — `isinstance(loss, float)`
6. `test_update_increments_buffer` — buffer grows after each real transition
7. `test_surprise_zero_on_perfect_prediction` — `surprise(inp, predicted_obs) ≈ 0`
8. `test_surprise_high_on_bad_prediction` — large error vector → high surprise
9. `test_snapshot_keys` — snapshot contains `config`, `step_count`, `buffer_size`
10. `test_build_world_model_returns_protocol` — `isinstance(wm, WorldModel)`
11. `test_concurrent_predict_safe` — 50 concurrent `predict()` calls, no race
12. `test_dream_rollout_accumulates_reward` — total_reward == sum of predicted_rewards

---

## Implementation Order (14 steps)

1. Define `TransitionBackend` + `PredictionTarget` enums
2. Define `ModelInput`, `ModelOutput`, `DreamRollout`, `WorldModelConfig` dataclasses
3. Define `WorldModel` Protocol (`@runtime_checkable`)
4. Implement `_mse()` helper + `build_world_model()` factory
5. Implement `InMemoryWorldModel.__init__()` — lock + deque + step counter
6. Implement `_forward()` stub (obs_dim-safe, noise-perturbed)
7. Implement `predict()` — lock + `_forward()`
8. Implement `update()` — buffer append + `_sgd_step()` + metrics
9. Implement `_sgd_step()` stub (MSE + `_wm_train_loss`)
10. Implement `dream_rollout()` — iterative `_forward()`, early-exit on done, metrics
11. Implement `surprise()` — predict + MSE + `_wm_surprise_score`
12. Implement `snapshot()`
13. Add 5 Prometheus metrics + PromQL + Grafana alert YAML
14. Write 12 test targets

---

## Phase 13 Roadmap

| Sub-phase | Component | Status |
|-----------|-----------|--------|
| 13.1 | WorldModel | 🟡 This page |
| 13.2 | DreamRolloutPlanner | ⏳ Planned |
| 13.3 | ModelBasedPolicyOptimizer | ⏳ Planned |
| 13.4 | SurpriseDetector | ⏳ Planned |
| 13.5 | WorldModelDashboard | ⏳ Planned |

**Phase 12 recap** — Coalition infrastructure complete:

| Sub-phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 12.1 | AgentRegistry | #352 | ✅ |
| 12.2 | NegotiationEngine | #355 | ✅ |
| 12.3 | CollaborationChannel | #358 | ✅ |
| 12.4 | ConsensusVoting | #361 | ✅ |
| 12.5 | CoalitionFormation | #364 | ✅ |
