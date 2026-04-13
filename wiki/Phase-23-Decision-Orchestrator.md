# Phase 23.5 — DecisionOrchestrator

> **Status**: ✅ Spec Complete — **PHASE 23 CAPSTONE** 🎉
> **Tracks**: Phase 23 — Decision Intelligence & Uncertainty Management
> **Depends on**: UncertaintyQuantifier (23.1), RiskAssessor (23.2), UtilityComputer (23.3), DecisionTreeSolver (23.4)
> **Feeds into**: CognitiveCycle (core), GoalDecomposer (10.2), PlanExecutor (10.3)

---

## Overview

The **DecisionOrchestrator** is the capstone component of Phase 23, composing all four preceding sub-modules into a unified decision pipeline. It receives decision requests from the CognitiveCycle, quantifies uncertainty, assesses risk, computes utility, optionally solves a decision tree, and returns a traced, auditable decision with full provenance.

Key design principles:
- **Composition over inheritance** — loose coupling via Protocol injection
- **6-phase pipeline** — each phase has independent failure handling (degraded mode)
- **Adaptive strategy selection** — simple decisions skip tree search, complex ones use MCTS
- **Emotional modulation** — AffectiveOrchestrator (21.5) adjusts risk tolerance and reference points
- **Full traceability** — every decision produces a `DecisionTrace` for reflection and audit

---

## Enums

### `DecisionPhase`

```python
class DecisionPhase(str, Enum):
    """Pipeline phase in the decision process."""
    IDLE = "idle"                    # Waiting for request
    FRAMING = "framing"              # Structuring the decision problem
    QUANTIFYING = "quantifying"      # Uncertainty quantification (23.1)
    ASSESSING = "assessing"          # Risk assessment (23.2)
    EVALUATING = "evaluating"        # Utility computation (23.3)
    SOLVING = "solving"              # Tree search / optimisation (23.4)
    VALIDATING = "validating"        # Risk gate + consistency check
    DECIDED = "decided"              # Final decision emitted
```

### `DecisionStrategy`

```python
class DecisionStrategy(str, Enum):
    """High-level decision approach."""
    ANALYTICAL = "analytical"        # Full pipeline: quantify → assess → utility → tree
    HEURISTIC = "heuristic"          # Fast path: utility ranking only (skip tree)
    INTUITIVE = "intuitive"          # Emotional/creative input dominant
    DELIBERATIVE = "deliberative"    # Extended analysis with VoI and scenarios
```

### `DecisionMode`

```python
class DecisionMode(str, Enum):
    """Operating mode for the orchestrator."""
    NORMAL = "normal"                # Full pipeline, all gates
    FAST = "fast"                    # Skip tree search, simplified risk
    CAUTIOUS = "cautious"           # Tighter risk thresholds, more scenarios
    EXPLORATORY = "exploratory"      # Lower risk aversion, creative alternatives
```

---

## Frozen Dataclasses

### `DecisionRequest`

```python
@dataclass(frozen=True)
class DecisionRequest:
    """Input to the decision pipeline."""
    id: str                                        # Unique request identifier
    description: str                               # Human-readable decision description
    alternatives: tuple[Alternative, ...]          # From UtilityComputer (23.3)
    context: dict[str, Any] = field(default_factory=dict)
    mode: DecisionMode = DecisionMode.NORMAL
    deadline_s: float | None = None                # Max time budget
    constraints: dict[str, Any] = field(default_factory=dict)
    emotional_state: dict[str, float] = field(default_factory=dict)  # From 21.5
    metadata: dict[str, Any] = field(default_factory=dict)
```

### `DecisionTrace`

```python
@dataclass(frozen=True)
class DecisionTrace:
    """Full audit trail of a decision."""
    request_id: str
    selected_alternative: str                      # Chosen alternative ID
    selected_utility: float                        # Utility of chosen alternative
    strategy_used: DecisionStrategy                # Which strategy was applied
    phases_completed: tuple[DecisionPhase, ...]    # Phases that ran successfully
    phases_degraded: tuple[DecisionPhase, ...]     # Phases that failed (degraded)
    uncertainty_estimate: UncertaintyEstimate | None = None
    risk_profile: RiskProfile | None = None
    utility_results: tuple[UtilityResult, ...] = ()
    solver_result: SolverResult | None = None
    voi_scores: dict[str, float] = field(default_factory=dict)
    emotional_modulation: dict[str, float] = field(default_factory=dict)
    computation_time_s: float = 0.0
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
```

### `OrchestratorConfig`

```python
@dataclass(frozen=True)
class OrchestratorConfig:
    """Configuration for DecisionOrchestrator."""
    default_mode: DecisionMode = DecisionMode.NORMAL
    default_strategy: DecisionStrategy = DecisionStrategy.ANALYTICAL
    max_trace_history: int = 1000                  # Deque size for trace storage
    risk_gate_enabled: bool = True                 # Reject unacceptable risk
    voi_threshold: float = 0.01                    # Minimum VoI to justify info gathering
    emotional_modulation_enabled: bool = True       # Allow affect to adjust parameters
    emotional_risk_scaling: float = 0.2            # Max risk tolerance adjustment from emotion
    fast_mode_timeout_s: float = 5.0               # Timeout for FAST mode
    cautious_mode_scenarios: int = 5               # Extra scenarios in CAUTIOUS mode
    tree_search_threshold: int = 3                 # Min alternatives to trigger tree search
```

---

## Protocol

```python
@runtime_checkable
class DecisionOrchestrator(Protocol):
    """Orchestrates the full decision intelligence pipeline."""

    async def decide(
        self,
        request: DecisionRequest,
    ) -> DecisionTrace:
        """Run the full decision pipeline and return traced decision."""
        ...

    async def batch_decide(
        self,
        requests: Sequence[DecisionRequest],
    ) -> tuple[DecisionTrace, ...]:
        """Process multiple decision requests (may parallelise)."""
        ...

    def get_traces(
        self,
        *,
        limit: int = 100,
    ) -> tuple[DecisionTrace, ...]:
        """Return recent decision traces for reflection/audit."""
        ...

    async def health(self) -> dict[str, Any]:
        """Health check across all sub-components."""
        ...
```

---

## Implementation — `AsyncDecisionOrchestrator`

```python
class AsyncDecisionOrchestrator:
    """
    Production implementation of DecisionOrchestrator.

    Composes 4 sub-components via constructor injection:
      - UncertaintyQuantifier (23.1)
      - RiskAssessor (23.2)
      - UtilityComputer (23.3)
      - DecisionTreeSolver (23.4)

    6-Phase Pipeline (decide):
      1. FRAMING      — parse request, select strategy, apply emotional modulation
      2. QUANTIFYING   — UncertaintyQuantifier.quantify() for each alternative
      3. ASSESSING     — RiskAssessor.assess() + scenario_analysis() for each
      4. EVALUATING    — UtilityComputer.rank() with risk-adjusted outcomes
      5. SOLVING       — DecisionTreeSolver.solve() (if analytical/deliberative)
      6. VALIDATING    — Risk gate (is_acceptable), consistency check, VoI check

    Per-phase error handling:
      - Each phase wrapped in try/except
      - On failure: log warning, mark phase as degraded, continue with partial data
      - Pipeline degrades gracefully — even with 0 successful phases, returns best-effort

    Emotional modulation (from AffectiveOrchestrator 21.5):
      - High anxiety  → lower risk tolerance (tighter VaR threshold)
      - High confidence → raise reference point
      - High curiosity → EXPLORATORY mode override
      - Modulation capped at emotional_risk_scaling (±20% default)

    Adaptive strategy selection:
      - 1-2 alternatives → HEURISTIC (utility ranking only)
      - 3+ alternatives with opponent → ANALYTICAL (full tree)
      - emotional_state dominates → INTUITIVE
      - deadline < fast_mode_timeout → FAST
      - High VoI detected → DELIBERATIVE (extra info gathering)

    Trace storage:
      - collections.deque(maxlen=max_trace_history)
      - get_traces() returns most recent N
      - Traces used by ReflectionCycle (16.5) for self-improvement
    """

    def __init__(
        self,
        quantifier: UncertaintyQuantifier,
        assessor: RiskAssessor,
        computer: UtilityComputer,
        solver: DecisionTreeSolver,
        config: OrchestratorConfig | None = None,
    ) -> None:
        self._quantifier = quantifier
        self._assessor = assessor
        self._computer = computer
        self._solver = solver
        self._config = config or OrchestratorConfig()
        self._traces: deque[DecisionTrace] = deque(maxlen=self._config.max_trace_history)
        self._phase: DecisionPhase = DecisionPhase.IDLE

    async def decide(
        self,
        request: DecisionRequest,
    ) -> DecisionTrace:
        """
        1. FRAMING: select strategy, apply emotional modulation
        2. QUANTIFYING: for each alternative, quantify uncertainty
        3. ASSESSING: for each alternative, assess risk
        4. EVALUATING: rank alternatives by utility
        5. SOLVING: optional tree search for complex decisions
        6. VALIDATING: risk gate + VoI check
        7. Build DecisionTrace, append to deque, return
        """
        start = time.monotonic()
        phases_completed: list[DecisionPhase] = []
        phases_degraded: list[DecisionPhase] = []
        uncertainty_est = None
        risk_prof = None
        utility_results: tuple[UtilityResult, ...] = ()
        solver_result = None
        emotional_mod: dict[str, float] = {}

        # --- Phase 1: FRAMING ---
        self._phase = DecisionPhase.FRAMING
        try:
            strategy = self._select_strategy(request)
            emotional_mod = self._apply_emotional_modulation(request)
            phases_completed.append(DecisionPhase.FRAMING)
        except Exception:
            strategy = self._config.default_strategy
            phases_degraded.append(DecisionPhase.FRAMING)

        # --- Phase 2: QUANTIFYING ---
        self._phase = DecisionPhase.QUANTIFYING
        try:
            # Quantify uncertainty for representative alternative
            if request.alternatives:
                preds = [a.outcomes[0] for a in request.alternatives if a.outcomes]
                uncertainty_est = await self._quantifier.quantify(preds, context=request.context)
            phases_completed.append(DecisionPhase.QUANTIFYING)
        except Exception:
            phases_degraded.append(DecisionPhase.QUANTIFYING)

        # --- Phase 3: ASSESSING ---
        self._phase = DecisionPhase.ASSESSING
        try:
            if request.alternatives:
                risk_prof = await self._assessor.assess(
                    list(request.alternatives[0].outcomes),
                    alternative_id=request.alternatives[0].id,
                    uncertainty=uncertainty_est,
                )
            phases_completed.append(DecisionPhase.ASSESSING)
        except Exception:
            phases_degraded.append(DecisionPhase.ASSESSING)

        # --- Phase 4: EVALUATING ---
        self._phase = DecisionPhase.EVALUATING
        try:
            utility_results = await self._computer.rank(request.alternatives)
            phases_completed.append(DecisionPhase.EVALUATING)
        except Exception:
            phases_degraded.append(DecisionPhase.EVALUATING)

        # --- Phase 5: SOLVING ---
        self._phase = DecisionPhase.SOLVING
        if strategy in (DecisionStrategy.ANALYTICAL, DecisionStrategy.DELIBERATIVE):
            try:
                tree = self._build_decision_tree(request, utility_results)
                solver_result = await self._solver.solve(tree)
                phases_completed.append(DecisionPhase.SOLVING)
            except Exception:
                phases_degraded.append(DecisionPhase.SOLVING)
        else:
            phases_completed.append(DecisionPhase.SOLVING)  # Skipped intentionally

        # --- Phase 6: VALIDATING ---
        self._phase = DecisionPhase.VALIDATING
        try:
            selected = self._select_best(utility_results, solver_result, risk_prof)
            phases_completed.append(DecisionPhase.VALIDATING)
        except Exception:
            selected = (request.alternatives[0].id, 0.0) if request.alternatives else ("none", 0.0)
            phases_degraded.append(DecisionPhase.VALIDATING)

        self._phase = DecisionPhase.DECIDED
        trace = DecisionTrace(
            request_id=request.id,
            selected_alternative=selected[0],
            selected_utility=selected[1],
            strategy_used=strategy,
            phases_completed=tuple(phases_completed),
            phases_degraded=tuple(phases_degraded),
            uncertainty_estimate=uncertainty_est,
            risk_profile=risk_prof,
            utility_results=utility_results,
            solver_result=solver_result,
            emotional_modulation=emotional_mod,
            computation_time_s=time.monotonic() - start,
            timestamp=time.monotonic(),
        )
        self._traces.append(trace)
        return trace

    async def batch_decide(
        self,
        requests: Sequence[DecisionRequest],
    ) -> tuple[DecisionTrace, ...]:
        """Process requests concurrently via asyncio.gather."""
        results = await asyncio.gather(*(self.decide(r) for r in requests))
        return tuple(results)

    def get_traces(self, *, limit: int = 100) -> tuple[DecisionTrace, ...]:
        return tuple(list(self._traces)[-limit:])

    async def health(self) -> dict[str, Any]:
        return {
            "phase": self._phase.value,
            "traces_stored": len(self._traces),
            "quantifier_calibrated": self._quantifier.is_calibrated(),
            "components": {
                "quantifier": type(self._quantifier).__name__,
                "assessor": type(self._assessor).__name__,
                "computer": type(self._computer).__name__,
                "solver": type(self._solver).__name__,
            },
        }
```

---

## Null Implementation

```python
class NullDecisionOrchestrator:
    """No-op for testing and DI wiring."""

    async def decide(self, request):
        alt_id = request.alternatives[0].id if request.alternatives else "none"
        return DecisionTrace(
            request_id=request.id, selected_alternative=alt_id,
            selected_utility=0.0, strategy_used=DecisionStrategy.HEURISTIC,
            phases_completed=(DecisionPhase.DECIDED,), phases_degraded=(),
        )

    async def batch_decide(self, requests):
        return tuple(await self.decide(r) for r in requests)

    def get_traces(self, *, limit=100):
        return ()

    async def health(self):
        return {"phase": "idle", "null": True}
```

---

## Factory

```python
def make_decision_orchestrator(
    quantifier: UncertaintyQuantifier | None = None,
    assessor: RiskAssessor | None = None,
    computer: UtilityComputer | None = None,
    solver: DecisionTreeSolver | None = None,
    config: OrchestratorConfig | None = None,
    *,
    null: bool = False,
) -> DecisionOrchestrator:
    if null:
        return NullDecisionOrchestrator()
    return AsyncDecisionOrchestrator(
        quantifier=quantifier or make_uncertainty_quantifier(null=True),
        assessor=assessor or make_risk_assessor(null=True),
        computer=computer or make_utility_computer(null=True),
        solver=solver or make_decision_tree_solver(null=True),
        config=config,
    )
```

---

## Full Phase 23 Pipeline

```
    ┌──────────────────────────────────────────────────────────────┐
    │                    DecisionRequest                            │
    │  alternatives, context, mode, emotional_state                │
    └──────────────────────────┬───────────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────────┐
    │  Phase 1: FRAMING                                            │
    │  Select strategy · Apply emotional modulation                │
    │  ┌─────────────────────────────────────────────────────────┐ │
    │  │ AffectiveOrchestrator (21.5) → risk tolerance adjust   │ │
    │  │ CreativeOrchestrator (22.5) → novel alternatives       │ │
    │  └─────────────────────────────────────────────────────────┘ │
    └──────────────────────────┬───────────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────────┐
    │  Phase 2: QUANTIFYING — UncertaintyQuantifier (23.1)         │
    │  ensemble predictions → decompose → calibrate → estimate     │
    │  Output: UncertaintyEstimate (epistemic/aleatoric/MI/ECE)    │
    └──────────────────────────┬───────────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────────┐
    │  Phase 3: ASSESSING — RiskAssessor (23.2)                    │
    │  Monte Carlo → VaR/CVaR → Sharpe → scenarios → Pareto       │
    │  Output: RiskProfile (category, tail prob, max drawdown)     │
    └──────────────────────────┬───────────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────────┐
    │  Phase 4: EVALUATING — UtilityComputer (23.3)                │
    │  prospect theory / EU / MAUT / maximin → rank alternatives   │
    │  Output: tuple[UtilityResult] ranked by utility              │
    └──────────────────────────┬───────────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────────┐
    │  Phase 5: SOLVING — DecisionTreeSolver (23.4)                │
    │  backward induction / minimax / MCTS / VoI                   │
    │  Output: SolverResult (optimal_action, expected_value)       │
    │  [skipped in HEURISTIC / FAST mode]                          │
    └──────────────────────────┬───────────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────────┐
    │  Phase 6: VALIDATING                                         │
    │  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐  │
    │  │ Risk Gate        │  │ Consistency  │  │ VoI Check      │  │
    │  │ is_acceptable()? │  │ solver ↔ rank│  │ gather info?   │  │
    │  └────────┬────────┘  └──────┬───────┘  └───────┬────────┘  │
    │           │ PASS              │ OK                │ below    │
    └───────────┼──────────────────┼──────────────────┼───────────┘
                │                  │                  │
    ┌───────────▼──────────────────▼──────────────────▼───────────┐
    │                    DecisionTrace                             │
    │  selected_alternative, utility, strategy, phases, timing     │
    │  → CognitiveCycle._decision_step()                           │
    │  → ReflectionCycle (16.5) for audit                          │
    │  → GoalDecomposer (10.2) for execution                       │
    └─────────────────────────────────────────────────────────────┘
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    async def _decision_step(self, perception: PerceptionResult) -> DecisionTrace:
        """
        Called during each cognitive cycle when a decision point is reached.
        
        1. Build alternatives from GoalDecomposer (10.2) sub-goals
        2. Attach emotional_state from AffectiveOrchestrator (21.5)
        3. Create DecisionRequest with context from WorldModel (13.1)
        4. Call DecisionOrchestrator.decide(request)
        5. Route selected_alternative to PlanExecutor (10.3)
        6. Store trace for ReflectionCycle (16.5)
        """
        alternatives = await self._goal_decomposer.get_alternatives(perception)
        emotional = await self._affective_orchestrator.get_state()
        request = DecisionRequest(
            id=f"cycle-{self._cycle_count}",
            description=f"Decision at cycle {self._cycle_count}",
            alternatives=alternatives,
            emotional_state=emotional,
            context=await self._world_model.get_context(),
        )
        trace = await self._decision_orchestrator.decide(request)
        await self._plan_executor.execute(trace.selected_alternative)
        return trace
```

---

## Cross-Phase Integration Map

```
    Phase 10 (Goal/Planning)     Phase 13 (World Model)
         │                              │
         │  alternatives                │  context/predictions
         ▼                              ▼
    ┌────────────────────────────────────────┐
    │          Phase 23 — Decision           │
    │          Intelligence Pipeline         │
    │                                        │
    │  23.1 UncertaintyQuantifier            │
    │  23.2 RiskAssessor                     │
    │  23.3 UtilityComputer                  │
    │  23.4 DecisionTreeSolver               │
    │  23.5 DecisionOrchestrator ◄───────────┤◄── Phase 21 (Emotional state)
    │                                        │◄── Phase 22 (Novel alternatives)
    └────────────┬───────────────────────────┘
                 │                        ▲
                 │  DecisionTrace          │  causal models
                 ▼                        │
    Phase 16 (Reflection)          Phase 20 (Reasoning)
         │
         │  self-improvement
         ▼
    Phase 14 (Self-Programming)
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `asi_decision_decide_total` | Counter | Total decide() calls |
| `asi_decision_decide_seconds` | Histogram | decide() end-to-end latency |
| `asi_decision_strategy_used` | Counter (label: strategy) | Strategy selection distribution |
| `asi_decision_phases_degraded` | Histogram | Number of degraded phases per decision |
| `asi_decision_risk_gate_rejections` | Counter | Decisions rejected by risk gate |

### PromQL Examples

```promql
# Decision rate
rate(asi_decision_decide_total[5m])

# Average decision time
histogram_quantile(0.50, asi_decision_decide_seconds_bucket)

# Degradation rate
rate(asi_decision_phases_degraded_sum[5m]) / rate(asi_decision_phases_degraded_count[5m])

# Risk gate rejection rate
rate(asi_decision_risk_gate_rejections[5m]) / rate(asi_decision_decide_total[5m])
```

### Grafana Alerts

```yaml
- alert: DecisionPipelineSlow
  expr: histogram_quantile(0.99, asi_decision_decide_seconds_bucket) > 30.0
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "Decision pipeline p99 latency exceeds 30s"

- alert: HighDegradationRate
  expr: |
    rate(asi_decision_phases_degraded_sum[5m]) / rate(asi_decision_phases_degraded_count[5m]) > 2.0
  for: 10m
  labels: { severity: critical }
  annotations:
    summary: "Average >2 degraded phases per decision — pipeline unhealthy"

- alert: RiskGateBlockingAll
  expr: rate(asi_decision_risk_gate_rejections[10m]) == rate(asi_decision_decide_total[10m])
  for: 10m
  labels: { severity: critical }
  annotations:
    summary: "Risk gate rejecting all decisions — may need threshold adjustment"
```

---

## Integration Notes

| Component | Direction | Contract |
|-----------|-----------|----------|
| **UncertaintyQuantifier (23.1)** | ← composed | quantify() in QUANTIFYING phase |
| **RiskAssessor (23.2)** | ← composed | assess() + scenario_analysis() in ASSESSING phase |
| **UtilityComputer (23.3)** | ← composed | rank() in EVALUATING phase |
| **DecisionTreeSolver (23.4)** | ← composed | solve() in SOLVING phase |
| **AffectiveOrchestrator (21.5)** | ← upstream | emotional_state → risk tolerance modulation |
| **CreativeOrchestrator (22.5)** | ← upstream | Novel alternatives injected into request |
| **ReasoningOrchestrator (20.5)** | ← upstream | Causal models structure tree topology |
| **WorldModel (13.1)** | ← upstream | Context predictions feed decision request |
| **GoalDecomposer (10.2)** | ← upstream | Sub-goals → alternatives |
| **PlanExecutor (10.3)** | → downstream | Selected alternative → execution plan |
| **ReflectionCycle (16.5)** | → downstream | DecisionTrace → audit + self-improvement |

---

## Mypy Strict Compliance

| Check | Status |
|-------|--------|
| `--strict` | ✅ Required |
| `--warn-return-any` | ✅ |
| `--disallow-untyped-defs` | ✅ |
| `@runtime_checkable` Protocol | ✅ |
| Frozen dataclasses only | ✅ |

---

## Test Targets (12)

| # | Test | Focus |
|---|------|-------|
| 1 | `test_decide_returns_frozen_trace` | Immutability + required fields |
| 2 | `test_decide_all_phases_completed` | No degraded phases with healthy components |
| 3 | `test_decide_degraded_phase_continues` | Pipeline continues when one component fails |
| 4 | `test_batch_decide_concurrent` | Multiple requests processed concurrently |
| 5 | `test_strategy_heuristic_skips_solver` | HEURISTIC mode doesn't call solver |
| 6 | `test_strategy_analytical_uses_solver` | ANALYTICAL mode calls solver |
| 7 | `test_emotional_modulation_adjusts_risk` | High anxiety → tighter risk threshold |
| 8 | `test_risk_gate_rejects_unacceptable` | High-risk alternative rejected |
| 9 | `test_get_traces_returns_recent` | Deque FIFO, limit respected |
| 10 | `test_health_reports_components` | Health check returns component names |
| 11 | `test_adaptive_strategy_selection` | Mode/alternatives → correct strategy |
| 12 | `test_null_orchestrator_passthrough` | NullDecisionOrchestrator returns defaults |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_decide_degraded_phase_continues():
    """If UncertaintyQuantifier fails, pipeline should continue with remaining phases."""
    # Use a quantifier that always raises
    class FailingQuantifier:
        async def quantify(self, *a, **kw): raise RuntimeError("boom")
        async def calibrate(self, *a, **kw): return 1.0
        async def decompose(self, *a, **kw): raise RuntimeError("boom")
        def is_calibrated(self): return False

    orch = AsyncDecisionOrchestrator(
        quantifier=FailingQuantifier(),
        assessor=make_risk_assessor(null=True),
        computer=make_utility_computer(null=True),
        solver=make_decision_tree_solver(null=True),
    )
    alt = Alternative(id="A", name="Alt A", outcomes=(10.0,))
    req = DecisionRequest(id="test", description="Test", alternatives=(alt,))
    trace = await orch.decide(req)
    assert DecisionPhase.QUANTIFYING in trace.phases_degraded
    assert DecisionPhase.EVALUATING in trace.phases_completed
    assert trace.selected_alternative == "A"

@pytest.mark.asyncio
async def test_emotional_modulation_adjusts_risk():
    """High anxiety should tighten risk tolerance in ASSESSING phase."""
    orch = AsyncDecisionOrchestrator(
        quantifier=make_uncertainty_quantifier(null=True),
        assessor=make_risk_assessor(null=True),
        computer=make_utility_computer(null=True),
        solver=make_decision_tree_solver(null=True),
        config=OrchestratorConfig(emotional_modulation_enabled=True),
    )
    alt = Alternative(id="A", name="Alt A", outcomes=(10.0,))
    anxious_req = DecisionRequest(
        id="anxious", description="Test",
        alternatives=(alt,),
        emotional_state={"anxiety": 0.9},
    )
    trace = await orch.decide(anxious_req)
    assert trace.emotional_modulation.get("risk_tolerance_adjustment", 0) < 0
```

---

## Implementation Order (14 steps)

1. Create `src/asi_build/decision/orchestrator/__init__.py`
2. Define `DecisionPhase`, `DecisionStrategy`, `DecisionMode` enums
3. Define `DecisionRequest`, `DecisionTrace`, `OrchestratorConfig` frozen dataclasses
4. Define `DecisionOrchestrator` Protocol with `@runtime_checkable`
5. Implement `AsyncDecisionOrchestrator.__init__` — inject 4 sub-components + config
6. Implement `_select_strategy()` — mode/alternatives/emotional dispatch
7. Implement `_apply_emotional_modulation()` — affect → risk tolerance/reference
8. Implement `decide()` Phase 1-2: FRAMING + QUANTIFYING
9. Implement `decide()` Phase 3-4: ASSESSING + EVALUATING
10. Implement `decide()` Phase 5-6: SOLVING + VALIDATING + trace assembly
11. Implement `batch_decide()`, `get_traces()`, `health()`
12. Implement `NullDecisionOrchestrator`
13. Implement `make_decision_orchestrator()` factory
14. Register Prometheus metrics + write 12 tests + verify mypy strict

---

## Phase 23 — FINAL Sub-Phase Tracker

| Sub-Phase | Component | Issue | Status |
|-----------|-----------|-------|--------|
| 23.1 | UncertaintyQuantifier | #529 | ✅ Spec |
| 23.2 | RiskAssessor | #530 | ✅ Spec |
| 23.3 | UtilityComputer | #531 | ✅ Spec |
| 23.4 | DecisionTreeSolver | #532 | ✅ Spec |
| 23.5 | DecisionOrchestrator | #533 | ✅ Spec |

> ### 🎉 PHASE 23 COMPLETE — Decision Intelligence & Uncertainty Management
>
> **5 sub-phases** spec'd · **5 wiki pages** · **5 issues** · **10+ discussions** · **60 test targets** · **70 implementation steps**
>
> The Decision Intelligence pipeline provides the ASI-Build cognitive architecture with principled decision-making under uncertainty, integrating Bayesian uncertainty quantification, Monte Carlo risk assessment, multi-framework utility computation, adaptive tree search, and a traced orchestration layer with emotional modulation and graceful degradation.
