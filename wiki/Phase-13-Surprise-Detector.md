# Phase 13.4 — SurpriseDetector

> **Sub-phase**: 13.4 | **Parent**: [Phase 13 — Model-Based Planning & World Grounding](Phase-13-World-Model) | **Issue**: #377

`SurpriseDetector` is a dedicated **anomaly-detection pipeline** that wraps `WorldModel.surprise()` and classifies prediction-error signals into a four-level severity taxonomy.  It replaces ad-hoc threshold comparisons scattered across `CognitiveCycle` with a single, configurable component.

---

## Enumerations

```python
from enum import Enum, auto

class DetectionStrategy(Enum):
    """Algorithm used to classify a raw surprise value."""
    THRESHOLD        = auto()   # simple raw > threshold (default)
    Z_SCORE          = auto()   # (x - mean) / std >= z_alert
    IQR              = auto()   # x > Q3 + k * IQR
    ISOLATION_FOREST = auto()   # sklearn-compatible scorer (plug-in)

class SeverityLevel(Enum):
    """Four-level severity taxonomy."""
    NORMAL = 0
    LOW    = 1
    MEDIUM = 2
    HIGH   = 3

    def escalated_from(self, previous: "SeverityLevel") -> bool:
        """True when this severity is strictly higher than previous."""
        return self.value > previous.value
```

---

## Data classes (all `frozen=True`)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SurpriseEpisode:
    step: int
    obs: tuple[float, ...]
    action: tuple[float, ...]
    raw_surprise: float
    severity: SeverityLevel
    score: float                   # normalised detector score
    strategy_used: DetectionStrategy

@dataclass(frozen=True)
class DetectorStats:
    window_mean: float
    window_std: float
    window_q1: float
    window_q3: float
    high_episode_count: int
    step_count: int
    current_severity: SeverityLevel

@dataclass(frozen=True)
class DetectorConfig:
    strategy: DetectionStrategy         = DetectionStrategy.Z_SCORE
    window_size: int                    = 2_000
    # THRESHOLD params
    threshold_low:    float             = 0.05
    threshold_medium: float             = 0.15
    threshold_high:   float             = 0.30
    # Z_SCORE params
    z_low:    float                     = 1.5
    z_medium: float                     = 2.5
    z_high:   float                     = 3.5
    # IQR params
    iqr_k_low:    float                 = 1.0
    iqr_k_medium: float                 = 1.5
    iqr_k_high:   float                 = 2.0
    # ISOLATION_FOREST
    if_contamination: float             = 0.05
    # alerting
    alert_cooldown_steps: int           = 50
    # curiosity integration
    gate_curiosity_on_high: bool        = True
    enabled: bool                       = True
```

---

## `AlertCallback` and `SurpriseDetector` Protocol

```python
from typing import Callable, Awaitable, Protocol, runtime_checkable

AlertCallback = Callable[[SurpriseEpisode], Awaitable[None]]

@runtime_checkable
class SurpriseDetector(Protocol):
    async def detect(
        self,
        obs: tuple[float, ...],
        action: tuple[float, ...],
        next_obs: tuple[float, ...],
        step: int,
    ) -> SurpriseEpisode: ...

    async def register_callback(
        self,
        severity: SeverityLevel,
        callback: AlertCallback,
    ) -> None: ...

    def stats(self) -> DetectorStats: ...
    def reset(self) -> None: ...
```

---

## `InMemorySurpriseDetector` — Reference Implementation

```python
import asyncio, statistics
from collections import deque

class InMemorySurpriseDetector:

    def __init__(self, world_model: WorldModel, config: DetectorConfig) -> None:
        self._wm      = world_model
        self._cfg     = config
        self._lock    = asyncio.Lock()
        self._window: deque[float] = deque(maxlen=config.window_size)
        self._callbacks: dict[SeverityLevel, list[AlertCallback]] = {
            s: [] for s in SeverityLevel
        }
        self._last_severity   = SeverityLevel.NORMAL
        self._last_alert_step = -config.alert_cooldown_steps
        self._high_count      = 0
        self._step_count      = 0

    # --- classifiers ---

    def _classify_threshold(self, raw: float) -> tuple[SeverityLevel, float]:
        c = self._cfg
        if raw >= c.threshold_high:   return SeverityLevel.HIGH,   raw
        if raw >= c.threshold_medium: return SeverityLevel.MEDIUM, raw
        if raw >= c.threshold_low:    return SeverityLevel.LOW,    raw
        return SeverityLevel.NORMAL, raw

    def _classify_z_score(self, raw: float) -> tuple[SeverityLevel, float]:
        if len(self._window) < 2:
            return SeverityLevel.NORMAL, 0.0
        mu  = statistics.mean(self._window)
        sig = statistics.stdev(self._window) or 1e-8
        z   = (raw - mu) / sig
        c = self._cfg
        if z >= c.z_high:   return SeverityLevel.HIGH,   z
        if z >= c.z_medium: return SeverityLevel.MEDIUM, z
        if z >= c.z_low:    return SeverityLevel.LOW,    z
        return SeverityLevel.NORMAL, z

    def _classify_iqr(self, raw: float) -> tuple[SeverityLevel, float]:
        if len(self._window) < 4:
            return SeverityLevel.NORMAL, 0.0
        sw = sorted(self._window)
        n  = len(sw)
        q1, q3 = sw[n // 4], sw[3 * n // 4]
        iqr = q3 - q1 or 1e-8
        score = (raw - q3) / iqr
        c = self._cfg
        if score >= c.iqr_k_high:   return SeverityLevel.HIGH,   score
        if score >= c.iqr_k_medium: return SeverityLevel.MEDIUM, score
        if score >= c.iqr_k_low:    return SeverityLevel.LOW,    score
        return SeverityLevel.NORMAL, score

    async def _classify(self, raw: float) -> tuple[SeverityLevel, float]:
        match self._cfg.strategy:
            case DetectionStrategy.THRESHOLD:        return self._classify_threshold(raw)
            case DetectionStrategy.Z_SCORE:          return self._classify_z_score(raw)
            case DetectionStrategy.IQR:              return self._classify_iqr(raw)
            case DetectionStrategy.ISOLATION_FOREST: return self._classify_threshold(raw)
            case _:                                  return SeverityLevel.NORMAL, 0.0

    async def _fire_callbacks(self, episode: SurpriseEpisode, step: int) -> None:
        cooldown_ok = (step - self._last_alert_step) >= self._cfg.alert_cooldown_steps
        escalated   = episode.severity.escalated_from(self._last_severity)
        if not (cooldown_ok and (escalated or episode.severity == SeverityLevel.HIGH)):
            return
        self._last_alert_step = step
        targets = [
            cb
            for sev, cbs in self._callbacks.items()
            for cb in cbs
            if episode.severity.value >= sev.value
        ]
        await asyncio.gather(*(cb(episode) for cb in targets), return_exceptions=True)

    # --- public API ---

    async def detect(self, obs, action, next_obs, step) -> SurpriseEpisode:
        raw = await self._wm.surprise(obs, action, next_obs)
        async with self._lock:
            self._window.append(raw)
            severity, score = await self._classify(raw)
            if severity == SeverityLevel.HIGH:
                self._high_count += 1
            self._step_count += 1
            episode = SurpriseEpisode(
                step=step, obs=obs, action=action,
                raw_surprise=raw, severity=severity,
                score=score, strategy_used=self._cfg.strategy,
            )
            await self._fire_callbacks(episode, step)
            self._last_severity = severity
        return episode

    async def register_callback(self, severity, callback) -> None:
        async with self._lock:
            self._callbacks[severity].append(callback)

    def stats(self) -> DetectorStats:
        w = list(self._window)
        if len(w) < 2:
            return DetectorStats(0, 0, 0, 0, self._high_count, self._step_count, self._last_severity)
        sw = sorted(w)
        n  = len(sw)
        return DetectorStats(
            window_mean=statistics.mean(w),
            window_std=statistics.stdev(w),
            window_q1=sw[n // 4],
            window_q3=sw[3 * n // 4],
            high_episode_count=self._high_count,
            step_count=self._step_count,
            current_severity=self._last_severity,
        )

    def reset(self) -> None:
        self._window.clear()
        self._high_count = 0
        self._step_count = 0
        self._last_severity = SeverityLevel.NORMAL
        self._last_alert_step = -self._cfg.alert_cooldown_steps
```

---

## Factory

```python
def build_surprise_detector(
    world_model: WorldModel,
    config: DetectorConfig | None = None,
    scorer=None,   # optional sklearn IsolationForest scorer
) -> SurpriseDetector:
    cfg = config or DetectorConfig()
    return InMemorySurpriseDetector(world_model, cfg)
```

---

## `CognitiveCycle` integration

```python
class CognitiveCycle:
    def __init__(self, ..., surprise_detector: SurpriseDetector | None = None):
        self._surprise_detector = surprise_detector

    async def _step(self, obs, action, next_obs, extrinsic_reward, step):
        # 1. Anomaly detection
        if self._surprise_detector and self._surprise_detector._cfg.enabled:
            episode  = await self._surprise_detector.detect(obs, action, next_obs, step)
            severity = episode.severity
        else:
            severity = SeverityLevel.NORMAL

        # 2. Curiosity gating
        if (
            self._curiosity
            and self._surprise_detector
            and self._surprise_detector._cfg.gate_curiosity_on_high
            and severity == SeverityLevel.HIGH
        ):
            bonus = 0.0   # suppress exploration during anomaly burst
        elif self._curiosity:
            event = await self._curiosity.compute_bonus(obs, action, next_obs, step)
            bonus = event.bonus
        else:
            bonus = 0.0

        await self._learner.update(obs, action, extrinsic_reward + bonus)
```

---

## Detection strategy decision guide

| Condition | Recommended strategy |
|---|---|
| Fixed observation scale, deterministic env | `THRESHOLD` |
| General purpose, WM improves over training | `Z_SCORE` (default) |
| Heavy-tailed / non-Gaussian surprise | `IQR` |
| Multi-dimensional obs, sklearn available | `ISOLATION_FOREST` |

---

## Z-score threshold tuning

| Sensitivity | `z_low` | `z_medium` | `z_high` |
|---|---|---|---|
| Very sensitive | 1.0 | 2.0 | 3.0 |
| Default | 1.5 | 2.5 | 3.5 |
| Conservative | 2.0 | 3.0 | 4.5 |

---

## Prometheus metrics + PromQL

```promql
# HIGH-severity rate
rate(asi_surprise_detections_total{severity="HIGH"}[5m])

# Fraction HIGH
rate(asi_surprise_detections_total{severity="HIGH"}[5m])
  / rate(asi_surprise_detections_total[5m])

# Window mean
asi_surprise_window_mean

# Grafana alert
- alert: SurpriseDetectorHighRate
  expr: >
    rate(asi_surprise_detections_total{severity="HIGH"}[5m])
    / rate(asi_surprise_detections_total[5m]) > 0.05
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "SurpriseDetector: >5% HIGH-severity detections"
```

---

## mypy checklist

| Symbol | Expected type |
|---|---|
| `SurpriseEpisode.severity` | `SeverityLevel` |
| `DetectorConfig.strategy` | `DetectionStrategy` |
| `AlertCallback` | `Callable[[SurpriseEpisode], Awaitable[None]]` |
| `_window` | `deque[float]` |
| `_callbacks` | `dict[SeverityLevel, list[AlertCallback]]` |
| `detect()` return | `SurpriseEpisode` |
| `stats()` return | `DetectorStats` |

---

## Test targets (12)

| # | Test name | What it covers |
|---|---|---|
| 1 | `test_threshold_classify_normal` | raw=0.01 → NORMAL |
| 2 | `test_threshold_classify_low` | raw=0.08 → LOW |
| 3 | `test_threshold_classify_medium` | raw=0.20 → MEDIUM |
| 4 | `test_threshold_classify_high` | raw=0.35 → HIGH |
| 5 | `test_z_score_cold_start_normal` | window < 2 → NORMAL |
| 6 | `test_z_score_escalation` | inject outlier, verify HIGH |
| 7 | `test_iqr_classify_low` | raw = Q3 + 1.1*IQR → LOW |
| 8 | `test_callback_fired_on_escalation` | register callback, verify awaited |
| 9 | `test_callback_cooldown_respected` | two highs within cooldown → one fire |
| 10 | `test_curiosity_gating` | severity=HIGH, gate=True → bonus=0 |
| 11 | `test_reset_clears_window` | reset() → stats zeroed |
| 12 | `test_protocol_compliance` | `isinstance(InMemory..., SurpriseDetector)` |

---

## Implementation order (14 steps)

1. Add `DetectionStrategy` + `SeverityLevel` enums to `cognitive_cycle/enums.py`
2. Add `SurpriseEpisode`, `DetectorStats`, `DetectorConfig` frozen dataclasses
3. Define `AlertCallback` type alias + `SurpriseDetector` Protocol
4. Implement `InMemorySurpriseDetector.__init__` + `_classify_threshold`
5. Implement `_classify_z_score` (statistics stdlib, no extra deps)
6. Implement `_classify_iqr` (percentile from sorted deque)
7. Implement `_classify` match-case dispatcher
8. Implement `_fire_callbacks` with cooldown guard
9. Implement `detect()` async method (lock-guarded)
10. Implement `register_callback()` + `stats()` + `reset()`
11. Add `build_surprise_detector()` factory
12. Wire into `CognitiveCycle._step()` with curiosity gating
13. Add 5 Prometheus metrics
14. Write 12 unit tests

---

## Phase 13 roadmap

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 13.1 | WorldModel | #368 | 🟡 In Progress |
| 13.2 | DreamPlanner | #371 | 🟡 In Progress |
| 13.3 | CuriosityModule | #374 | 🟡 In Progress |
| 13.4 | SurpriseDetector | #377 | 🟡 In Progress |
| 13.5 | WorldModelDashboard | TBD | ⏳ Planned |

---

*Phase 12 recap: [AgentRegistry](Phase-12-Agent-Registry) · [NegotiationEngine](Phase-12-Negotiation-Engine) · [CollaborationChannel](Phase-12-Collaboration-Channel) · [ConsensusVoting](Phase-12-Consensus-Voting) · [CoalitionFormation](Phase-12-Coalition-Formation)*
