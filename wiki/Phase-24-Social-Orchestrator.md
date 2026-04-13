# Phase 24.5 — SocialOrchestrator: Unified Social Cognition Pipeline

> **Issue**: [#550](https://github.com/web3guru888/asi-build/issues/550) | **Show & Tell**: [#559](https://github.com/web3guru888/asi-build/discussions/559) | **Q&A**: [#560](https://github.com/web3guru888/asi-build/discussions/560)

## Overview

The `SocialOrchestrator` is the **capstone component** of Phase 24, composing BeliefTracker (24.1), IntentionRecognizer (24.2), PerspectiveTaker (24.3), and SocialPredictor (24.4) into a unified **social cognition pipeline**. It implements a complete Theory of Mind coordination loop: observe → model beliefs → infer intentions → simulate perspectives → predict dynamics → select strategy → act.

## Architecture

### Social Cognition Cycle

The SocialOrchestrator runs a 6-phase cycle that processes social observations into actionable strategies:

```
              SocialObservation
                    │
    ┌───────────────┼───────────────┐
    │               ▼               │
    │  ┌─────────────────────────┐  │
    │  │   Phase 1: OBSERVING    │  │  Parse actions & messages
    │  └────────────┬────────────┘  │
    │               │               │
    │  ┌────────────▼────────────┐  │
    │  │ Phase 2: MODELING       │  │  BeliefTracker 24.1
    │  │ Bayesian belief update  │  │  AGM revision if conflict
    │  └────────────┬────────────┘  │
    │               │               │
    │  ┌────────────▼────────────┐  │
    │  │ Phase 3: INFERRING      │  │  IntentionRecognizer 24.2
    │  │ Plan recognition + BDI  │  │  Bayesian inverse planning
    │  └────────────┬────────────┘  │
    │               │               │
    │  ┌────────────▼────────────┐  │
    │  │ Phase 4: SIMULATING     │  │  PerspectiveTaker 24.3
    │  │ Level-k recursion       │  │  [parallel for N agents]
    │  └────────────┬────────────┘  │
    │               │               │
    │  ┌────────────▼────────────┐  │
    │  │ Phase 5: PREDICTING     │  │  SocialPredictor 24.4
    │  │ Trust + coalitions      │  │  Replicator dynamics
    │  └────────────┬────────────┘  │
    │               │               │
    │  ┌────────────▼────────────┐  │
    │  │ Phase 6: STRATEGIZING   │  │  Generate + evaluate
    │  │ DecisionOrch 23.5       │  │  Risk-adjust + ethics
    │  └────────────┬────────────┘  │
    │               │               │
    └───────────────┼───────────────┘
                    ▼
           SocialCycleResult
          (context + strategy)
```

## Data Structures

### Enums

```python
class SocialPhase(enum.Enum):
    IDLE = "idle"
    OBSERVING = "observing"
    MODELING_BELIEFS = "modeling"
    INFERRING_INTENT = "inferring"
    SIMULATING = "simulating"
    PREDICTING = "predicting"
    STRATEGIZING = "strategizing"
    ACTING = "acting"

class SocialStrategyType(enum.Enum):
    COOPERATIVE = "cooperative"       # Maximize joint value
    COMPETITIVE = "competitive"       # Maximize own value
    RECIPROCAL = "reciprocal"        # Tit-for-tat
    DECEPTIVE = "deceptive"          # Strategic information hiding
    PERSUASIVE = "persuasive"        # Influence beliefs/intentions
    ALTRUISTIC = "altruistic"        # Sacrifice for group
    DEFENSIVE = "defensive"          # Protect against exploitation
```

### Frozen Dataclasses

```python
@dataclass(frozen=True)
class SocialObservation:
    observer_id: str
    observed_agents: tuple[str, ...]
    actions: tuple[ObservedAction, ...]
    messages: tuple[str, ...]
    context: Mapping[str, Any]
    timestamp_ms: int

@dataclass(frozen=True)
class SocialContext:
    agents: tuple[str, ...]
    belief_states: Mapping[str, BeliefState]
    intention_models: Mapping[str, BDIState]
    perspectives: Mapping[str, Perspective]
    social_graph: SocialGraph
    predictions: tuple[SocialPrediction, ...]
    timestamp_ms: int
    phase: SocialPhase

@dataclass(frozen=True)
class SocialStrategy:
    strategy_type: SocialStrategyType
    target_agents: tuple[str, ...]
    actions: tuple[str, ...]
    reasoning: str
    expected_value: float
    risk: float
    confidence: float
    requires_deception: bool

@dataclass(frozen=True)
class SocialCycleResult:
    context: SocialContext
    selected_strategy: SocialStrategy
    alternatives: tuple[SocialStrategy, ...]
    cycle_ms: int
    phase_timings: Mapping[SocialPhase, int]

@dataclass(frozen=True)
class SocialOrchestratorConfig:
    cycle_timeout_ms: int = 2000
    max_agents_modeled: int = 50
    strategy_candidates: int = 5
    deception_allowed: bool = False
    min_strategy_confidence: float = 0.3
    parallel_simulation: bool = True
```

## Protocol

```python
@runtime_checkable
class SocialOrchestrator(Protocol):
    async def analyze_social_situation(self, observation: SocialObservation) -> SocialContext: ...
    async def plan_social_action(self, context: SocialContext,
                                  our_goals: tuple[str, ...]) -> SocialCycleResult: ...
    async def update_social_model(self, observation: SocialObservation) -> None: ...
    async def get_social_context(self) -> SocialContext: ...
    async def run_social_cycle(self, observation: SocialObservation,
                                our_goals: tuple[str, ...]) -> SocialCycleResult: ...
    async def get_agent_profile(self, agent_id: str) -> Mapping[str, Any]: ...
```

## Implementation: AsyncSocialOrchestrator

### Internal State

```python
class AsyncSocialOrchestrator:
    _belief_tracker: BeliefTracker
    _intention_recognizer: IntentionRecognizer
    _perspective_taker: PerspectiveTaker
    _social_predictor: SocialPredictor
    _decision_orch: DecisionOrchestrator | None
    _config: SocialOrchestratorConfig
    _current_context: SocialContext | None
    _cycle_history: deque[SocialCycleResult]  # maxlen=100
    _lock: asyncio.Lock
    _phase: SocialPhase
```

### analyze_social_situation — Full Pipeline

```python
async def analyze_social_situation(self, observation):
    async with self._lock:
        timings = {}
        
        # Phase 1: OBSERVING
        self._phase = SocialPhase.OBSERVING
        t = time.monotonic_ns()
        actions_by_agent = self._categorize(observation)
        timings[SocialPhase.OBSERVING] = elapsed_ms(t)
        
        # Phase 2: MODELING
        self._phase = SocialPhase.MODELING_BELIEFS
        t = time.monotonic_ns()
        belief_states = {}
        for agent_id, actions in actions_by_agent.items():
            for action in actions:
                for prop, lr in self._extract_propositions(action):
                    await self._belief_tracker.update_belief(agent_id, prop, lr)
            belief_states[agent_id] = await self._belief_tracker.get_agent_model(agent_id)
        timings[SocialPhase.MODELING_BELIEFS] = elapsed_ms(t)
        
        # Phase 3: INFERRING
        self._phase = SocialPhase.INFERRING_INTENT
        t = time.monotonic_ns()
        intent_models = {}
        for agent_id, actions in actions_by_agent.items():
            for action in actions:
                await self._intention_recognizer.observe_action(action)
            intent_models[agent_id] = await self._intention_recognizer.get_bdi_state(agent_id)
        timings[SocialPhase.INFERRING_INTENT] = elapsed_ms(t)
        
        # Phase 4: SIMULATING (parallel)
        self._phase = SocialPhase.SIMULATING
        t = time.monotonic_ns()
        key_agents = list(actions_by_agent.keys())[:self._config.max_agents_modeled]
        if self._config.parallel_simulation:
            results = await asyncio.gather(
                *[self._safe_perspective(a) for a in key_agents],
                return_exceptions=True
            )
            perspectives = {a: r for a, r in zip(key_agents, results) if not isinstance(r, Exception)}
        else:
            perspectives = {}
            for a in key_agents:
                perspectives[a] = await self._safe_perspective(a)
        timings[SocialPhase.SIMULATING] = elapsed_ms(t)
        
        # Phase 5: PREDICTING
        self._phase = SocialPhase.PREDICTING
        t = time.monotonic_ns()
        social_graph = await self._social_predictor.get_social_graph()
        predictions = []
        for agent_id in key_agents:
            preds = await self._social_predictor.predict_behavior(agent_id, observation.context)
            predictions.extend(preds)
        timings[SocialPhase.PREDICTING] = elapsed_ms(t)
        
        # Compose context
        context = SocialContext(
            agents=tuple(key_agents), belief_states=belief_states,
            intention_models=intent_models, perspectives=perspectives,
            social_graph=social_graph, predictions=tuple(predictions),
            timestamp_ms=observation.timestamp_ms, phase=SocialPhase.IDLE
        )
        self._current_context = context
        return context
```

### plan_social_action — Strategy Selection

```python
async def plan_social_action(self, context, our_goals):
    candidates = []
    
    for strategy_type in SocialStrategyType:
        if strategy_type == SocialStrategyType.DECEPTIVE and not self._config.deception_allowed:
            continue
        
        strategy = self._generate_strategy(strategy_type, context, our_goals)
        
        # Simulate opponent responses
        responses = {}
        for target in strategy.target_agents:
            if target in context.perspectives:
                sim = await self._perspective_taker.predict_response(
                    target, strategy.actions[0] if strategy.actions else ""
                )
                responses[target] = sim
        
        # Evaluate expected value
        if self._decision_orch:
            ev = await self._decision_orch.evaluate_option(strategy.actions, responses)
        else:
            ev = strategy.expected_value
        
        # Risk assessment
        risk = self._assess_strategy_risk(strategy, context)
        
        score = ev - 0.5 * risk  # λ = 0.5 default risk aversion
        candidates.append((strategy._replace(expected_value=ev, risk=risk), score))
    
    candidates.sort(key=lambda x: -x[1])
    selected = candidates[0][0] if candidates else self._defensive_fallback(context)
    
    if selected.confidence < self._config.min_strategy_confidence:
        selected = self._defensive_fallback(context)
    
    return SocialCycleResult(context, selected, tuple(c[0] for c in candidates[1:]), ...)
```

### Degraded Mode

```python
async def _safe_perspective(self, agent_id):
    try:
        return await asyncio.wait_for(
            self._perspective_taker.take_perspective(agent_id),
            timeout=self._config.cycle_timeout_ms / (4 * 1000.0)
        )
    except (asyncio.TimeoutError, Exception):
        if self._current_context and agent_id in self._current_context.perspectives:
            return self._current_context.perspectives[agent_id]
        return Perspective(agent_id, {}, {}, (), ReasoningLevel.NAIVE, "fallback", 0.1)
```

### Agent Profile Aggregation

```python
async def get_agent_profile(self, agent_id):
    belief_state = await self._belief_tracker.get_agent_model(agent_id)
    bdi_state = await self._intention_recognizer.get_bdi_state(agent_id)
    perspective = await self._perspective_taker.take_perspective(agent_id)
    social_graph = await self._social_predictor.get_social_graph()
    
    trust_scores = social_graph.trust_matrix.get(agent_id, {})
    coalitions = [c for c in social_graph.coalitions if agent_id in c.members]
    
    return {
        "agent_id": agent_id,
        "beliefs": belief_state,
        "intentions": bdi_state,
        "perspective": perspective,
        "trust_given": trust_scores,
        "coalitions": coalitions,
        "social_role": self._classify_role(agent_id, social_graph),
    }
```

## Strategy Selection Framework

### Strategy Types & Heuristics

| Strategy | When Selected | Risk Level |
|----------|--------------|-----------|
| COOPERATIVE | High mutual trust, aligned goals | Low |
| COMPETITIVE | Low trust, competing goals | Medium |
| RECIPROCAL | Moderate trust, repeated interaction | Low |
| PERSUASIVE | Belief disagreements exist | Medium |
| ALTRUISTIC | High group value, low personal cost | Low |
| DEFENSIVE | High uncertainty, unknown agents | Lowest |
| DECEPTIVE | Only if deception_allowed=True | Highest |

### Budget Allocation

| Phase | Budget (ms) | Typical |
|-------|------------|---------|
| OBSERVING | 50 | 10 |
| MODELING | 200 | 50 |
| INFERRING | 300 | 100 |
| SIMULATING | 600 | 300 |
| PREDICTING | 350 | 150 |
| STRATEGIZING | 500 | 200 |
| **Total** | **2000** | **810** |

## Integration Points

| Component | Direction | Interface |
|-----------|-----------|-----------|
| BeliefTracker 24.1 | ← compose | Belief management |
| IntentionRecognizer 24.2 | ← compose | Intention inference |
| PerspectiveTaker 24.3 | ← compose | Viewpoint simulation |
| SocialPredictor 24.4 | ← compose | Social dynamics |
| DecisionOrchestrator 23.5 | ← input | Strategy evaluation |
| CommunicationOrchestrator 19.5 | ← input | Message streams |
| CreativeOrchestrator 22.5 | ← input | Creative strategies |
| CognitiveCycle (core) | → output | Social step |

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_social_cycles_total` | Counter | Total cycles |
| `asi_social_cycle_seconds` | Histogram | Full cycle latency |
| `asi_social_phase_seconds` | Histogram | Per-phase latency |
| `asi_social_strategy_selected` | Counter | By type |
| `asi_social_degraded_cycles_total` | Counter | Degraded cycles |

### PromQL Examples

```promql
# Cycle latency p95
histogram_quantile(0.95, asi_social_cycle_seconds_bucket)

# Strategy distribution
increase(asi_social_strategy_selected[1h])

# Degraded cycle rate
rate(asi_social_degraded_cycles_total[5m]) / rate(asi_social_cycles_total[5m])
```

### Grafana Alerts

```yaml
- alert: SocialCycleBudgetExceeded
  expr: histogram_quantile(0.95, asi_social_cycle_seconds_bucket) > 2.0
  for: 5m
  annotations:
    summary: "Social cognition cycle p95 > 2s budget"

- alert: HighDegradedCycleRate
  expr: rate(asi_social_degraded_cycles_total[5m]) / rate(asi_social_cycles_total[5m]) > 0.1
  for: 5m
  annotations:
    summary: "Degraded social cycles > 10%"
```

## Test Targets (12)

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_full_cycle_all_phases_execute` | All 6 phases run |
| 2 | `test_parallel_perspective_simulation` | asyncio.gather |
| 3 | `test_strategy_selection_maximizes_ev` | Highest EV selected |
| 4 | `test_deception_blocked_when_disabled` | Filtered if flag=False |
| 5 | `test_degraded_mode_component_timeout` | Timeout → cached + degraded |
| 6 | `test_agent_profile_aggregation` | Merges all components |
| 7 | `test_incremental_update_lightweight` | Skips full cycle |
| 8 | `test_cycle_timeout_budget_respected` | Within timeout_ms |
| 9 | `test_ethical_constraint_no_deception` | No deception strategies |
| 10 | `test_context_snapshot_consistency` | Reflects last analysis |
| 11 | `test_cycle_history_bounded` | deque maxlen=100 |
| 12 | `test_null_social_orchestrator_no_ops` | Empty result |

## Implementation Order

1. `SocialPhase` + `SocialStrategyType` enums
2. `SocialObservation` dataclass
3. `SocialContext` + `SocialStrategy` + `SocialCycleResult` dataclasses
4. `SocialOrchestratorConfig` dataclass
5. `SocialOrchestrator` Protocol
6. `AsyncSocialOrchestrator.__init__`
7. `analyze_social_situation` — 6-phase pipeline
8. `plan_social_action` — strategy generation + eval
9. `run_social_cycle` — compose analyze + plan
10. `update_social_model` — lightweight
11. `get_social_context` + `get_agent_profile`
12. Degraded mode fallbacks
13. `NullSocialOrchestrator` no-op
14. `make_social_orchestrator()` factory + metrics + tests

## Phase 24 — Complete Tracker 🎉

| # | Component | Issue | S&T | Q&A | Wiki | Status |
|---|-----------|-------|-----|-----|------|--------|
| 24.1 | BeliefTracker | [#546](https://github.com/web3guru888/asi-build/issues/546) | [#551](https://github.com/web3guru888/asi-build/discussions/551) | [#552](https://github.com/web3guru888/asi-build/discussions/552) | ✅ | ✅ Spec'd |
| 24.2 | IntentionRecognizer | [#547](https://github.com/web3guru888/asi-build/issues/547) | [#553](https://github.com/web3guru888/asi-build/discussions/553) | [#554](https://github.com/web3guru888/asi-build/discussions/554) | ✅ | ✅ Spec'd |
| 24.3 | PerspectiveTaker | [#548](https://github.com/web3guru888/asi-build/issues/548) | [#555](https://github.com/web3guru888/asi-build/discussions/555) | [#556](https://github.com/web3guru888/asi-build/discussions/556) | ✅ | ✅ Spec'd |
| 24.4 | SocialPredictor | [#549](https://github.com/web3guru888/asi-build/issues/549) | [#557](https://github.com/web3guru888/asi-build/discussions/557) | [#558](https://github.com/web3guru888/asi-build/discussions/558) | ✅ | ✅ Spec'd |
| 24.5 | SocialOrchestrator | [#550](https://github.com/web3guru888/asi-build/issues/550) | [#559](https://github.com/web3guru888/asi-build/discussions/559) | [#560](https://github.com/web3guru888/asi-build/discussions/560) | ✅ | ✅ Spec'd |

---

*Phase 24 complete. ASI-Build now has Theory of Mind—the ability to model other minds, predict social dynamics, and act strategically in multi-agent environments.*
