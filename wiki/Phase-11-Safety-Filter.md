# Phase 11.1 — SafetyFilter: Constitutional Ruleset Gating

**Issue**: [#337](https://github.com/web3guru888/asi-build/issues/337)  
**Phase**: 11.1 — Safety & Alignment  
**Status**: In spec  
**Discussions**: [Show & Tell #338](https://github.com/web3guru888/asi-build/discussions/338) · [Q&A #339](https://github.com/web3guru888/asi-build/discussions/339)

---

## Overview

`SafetyFilter` is the constitutional alignment layer of ASI:BUILD. Every `Goal` and `SubTask` passes through a configurable ruleset before entering the Phase 10 autonomy loop. Violations are classified by severity — `INFO`, `WARN`, `BLOCK`, or `CRITICAL` — with `CRITICAL` violations immediately pausing the autonomy loop.

---

## Data Model

```python
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

class ViolationSeverity(Enum):
    INFO = "info"          # log only
    WARN = "warn"          # log + flag goal, proceed
    BLOCK = "block"        # reject goal / sub-task
    CRITICAL = "critical"  # reject + alert + pause autonomy loop

@dataclass(frozen=True)
class SafetyViolation:
    rule_id: str
    severity: ViolationSeverity
    subject_id: str           # goal_id or subtask_id
    subject_type: str         # "goal" or "subtask"
    message: str
    timestamp: float = field(default_factory=time.monotonic)

@dataclass(frozen=True)
class SafetyVerdict:
    subject_id: str
    allowed: bool             # False if any BLOCK/CRITICAL violation
    violations: tuple[SafetyViolation, ...]
    evaluated_at: float = field(default_factory=time.monotonic)

@dataclass(frozen=True)
class SafetyRule:
    rule_id: str
    description: str
    severity: ViolationSeverity

@dataclass(frozen=True)
class SafetyConfig:
    max_goal_description_len: int = 2048
    allowed_capability_prefixes: frozenset[str] = frozenset({"local:", "federation:"})
    blocked_capability_patterns: frozenset[str] = frozenset({"network:external", "exec:arbitrary"})
    max_subtasks_per_graph: int = 128
    max_priority_auto_escalate: int = 3   # GoalPriority.HIGH
    pause_on_critical: bool = True
```

---

## `SafetyFilter` Protocol

```python
@runtime_checkable
class SafetyFilter(Protocol):
    async def check_goal(self, goal: "Goal") -> SafetyVerdict: ...
    async def check_subtask(self, subtask: "SubTask") -> SafetyVerdict: ...
    async def check_task_graph(self, graph: "TaskGraph") -> list[SafetyVerdict]: ...
    def register_rule(self, rule: SafetyRule, predicate: Any) -> None: ...
    def violations_since(self, since_ts: float) -> list[SafetyViolation]: ...
```

---

## Constitutional Ruleset (SR-001 to SR-007)

| Rule ID | Target | Severity | Logic |
|---------|--------|----------|-------|
| `SR-001` | Goal | BLOCK | `len(description) > max_goal_description_len` |
| `SR-002` | Goal | BLOCK | `priority == CRITICAL` without `allow_critical=True` |
| `SR-003` | SubTask | BLOCK | `required_caps` contains a blocked capability pattern |
| `SR-004` | SubTask | WARN | `required_caps` prefix not in `allowed_capability_prefixes` |
| `SR-005` | TaskGraph | BLOCK | Total subtask count > `max_subtasks_per_graph` |
| `SR-006` | Goal | WARN | Description matches `https?://` regex |
| `SR-007` | Goal | CRITICAL | `goal_type` in hardcoded denylist (`self_modify_runtime`, `disable_safety_filter`, `exfiltrate_data`) |

---

## `InMemorySafetyFilter`

```python
import asyncio, re
from prometheus_client import Counter, Gauge, Histogram

# Module-level Prometheus metrics
_checks_total = Counter("asi_safety_checks_total", "Checks performed", ["subject_type", "result"])
_violations_total = Counter("asi_safety_violations_total", "Violations fired", ["rule_id", "severity"])
_safety_paused = Gauge("asi_safety_paused", "1 if autonomy loop paused by CRITICAL")
_rules_registered = Gauge("asi_safety_rules_registered", "Total rules in ruleset")
_check_duration = Histogram("asi_safety_check_duration_seconds", "Check latency", ["subject_type"])

class InMemorySafetyFilter:
    def __init__(self, config: SafetyConfig | None = None) -> None:
        self._config = config or SafetyConfig()
        self._rules: list[tuple[SafetyRule, Any]] = []
        self._violations: list[SafetyViolation] = []
        self._lock = asyncio.Lock()
        self._paused = False
        self._register_constitutional_rules()

    def _register_constitutional_rules(self) -> None:
        cfg = self._config
        DENYLIST = frozenset({"self_modify_runtime", "disable_safety_filter", "exfiltrate_data"})
        rules = [
            (SafetyRule("SR-001", "Goal description too long", ViolationSeverity.BLOCK),
             lambda g: len(g.description) > cfg.max_goal_description_len),
            (SafetyRule("SR-002", "CRITICAL priority requires allow_critical flag", ViolationSeverity.BLOCK),
             lambda g: g.priority.value == "critical" and not getattr(g, "allow_critical", False)),
            (SafetyRule("SR-006", "Goal description contains URL", ViolationSeverity.WARN),
             lambda g: bool(re.search(r"https?://", g.description))),
            (SafetyRule("SR-007", "Goal type in CRITICAL denylist", ViolationSeverity.CRITICAL),
             lambda g: getattr(g, "goal_type", "") in DENYLIST),
        ]
        for rule, predicate in rules:
            self.register_rule(rule, predicate)

    def register_rule(self, rule: SafetyRule, predicate: Any) -> None:
        self._rules.append((rule, predicate))
        _rules_registered.set(len(self._rules))

    async def check_goal(self, goal: "Goal") -> SafetyVerdict:
        viols: list[SafetyViolation] = []
        for rule, predicate in self._rules:
            try:
                if predicate(goal):
                    v = SafetyViolation(rule.rule_id, rule.severity, goal.goal_id, "goal", rule.description)
                    viols.append(v)
                    if rule.severity == ViolationSeverity.CRITICAL and self._config.pause_on_critical:
                        self._paused = True
                        _safety_paused.set(1)
            except Exception:
                pass
        async with self._lock:
            self._violations.extend(viols)
        for v in viols:
            _violations_total.labels(rule_id=v.rule_id, severity=v.severity.value).inc()
        allowed = not any(v.severity in (ViolationSeverity.BLOCK, ViolationSeverity.CRITICAL) for v in viols)
        _checks_total.labels(subject_type="goal", result="allowed" if allowed else "blocked").inc()
        return SafetyVerdict(goal.goal_id, allowed, tuple(viols))

    async def check_subtask(self, subtask: "SubTask") -> SafetyVerdict:
        viols: list[SafetyViolation] = []
        cfg = self._config
        for cap in subtask.required_caps:
            for pattern in cfg.blocked_capability_patterns:
                if pattern in cap:
                    viols.append(SafetyViolation("SR-003", ViolationSeverity.BLOCK, subtask.subtask_id, "subtask", f"Blocked cap: {cap}"))
        for cap in subtask.required_caps:
            if not any(cap.startswith(pfx) for pfx in cfg.allowed_capability_prefixes):
                viols.append(SafetyViolation("SR-004", ViolationSeverity.WARN, subtask.subtask_id, "subtask", f"Unknown cap prefix: {cap}"))
        async with self._lock:
            self._violations.extend(viols)
        for v in viols:
            _violations_total.labels(rule_id=v.rule_id, severity=v.severity.value).inc()
        allowed = not any(v.severity in (ViolationSeverity.BLOCK, ViolationSeverity.CRITICAL) for v in viols)
        _checks_total.labels(subject_type="subtask", result="allowed" if allowed else "blocked").inc()
        return SafetyVerdict(subtask.subtask_id, allowed, tuple(viols))

    async def check_task_graph(self, graph: "TaskGraph") -> list[SafetyVerdict]:
        verdicts: list[SafetyVerdict] = []
        if len(graph.subtasks) > self._config.max_subtasks_per_graph:
            v = SafetyViolation("SR-005", ViolationSeverity.BLOCK, graph.root_goal_id, "subtask",
                f"Graph has {len(graph.subtasks)} subtasks (max {self._config.max_subtasks_per_graph})")
            async with self._lock:
                self._violations.append(v)
            _violations_total.labels(rule_id="SR-005", severity="block").inc()
            verdicts.append(SafetyVerdict(graph.root_goal_id, False, (v,)))
        for subtask in graph.subtasks.values():
            verdicts.append(await self.check_subtask(subtask))
        _checks_total.labels(subject_type="graph", result="allowed" if all(v.allowed for v in verdicts) else "blocked").inc()
        return verdicts

    def violations_since(self, since_ts: float) -> list[SafetyViolation]:
        return [v for v in self._violations if v.timestamp >= since_ts]

    def resume(self, operator_id: str = "operator") -> None:
        """Clear CRITICAL pause. Call only after investigating the violation."""
        self._paused = False
        _safety_paused.set(0)
```

---

## `SafeGoalRegistry` + `SafeGoalDecomposer` Wrappers

```python
class SafeGoalRegistry:
    """Thin wrapper: check_goal() before register()."""
    def __init__(self, registry: GoalRegistry, safety: SafetyFilter) -> None:
        self._registry = registry
        self._safety = safety

    async def register(self, goal: Goal) -> str:
        verdict = await self._safety.check_goal(goal)
        if not verdict.allowed:
            blocked_rules = [v.rule_id for v in verdict.violations
                             if v.severity in (ViolationSeverity.BLOCK, ViolationSeverity.CRITICAL)]
            raise RuntimeError(f"Goal blocked by SafetyFilter: {blocked_rules}")
        return await self._registry.register(goal)


class SafeGoalDecomposer:
    """Thin wrapper: check_task_graph() after decompose(), before dispatch()."""
    def __init__(self, decomposer: GoalDecomposer, safety: SafetyFilter) -> None:
        self._decomposer = decomposer
        self._safety = safety

    async def decompose(self, goal: Goal) -> TaskGraph:
        graph = await self._decomposer.decompose(goal)
        verdicts = await self._safety.check_task_graph(graph)
        blocked = [v for v in verdicts if not v.allowed]
        if blocked:
            raise RuntimeError(f"TaskGraph blocked by SafetyFilter: {[v.subject_id for v in blocked]}")
        return graph
```

---

## `build_safety_filter()` Factory

```python
def build_safety_filter(config: SafetyConfig | None = None) -> InMemorySafetyFilter:
    """Factory — returns InMemorySafetyFilter with constitutional rules pre-loaded."""
    return InMemorySafetyFilter(config)
```

---

## CognitiveCycle Integration

```python
class CognitiveCycle:
    def __init__(self, ..., safety_filter: SafetyFilter) -> None:
        ...
        self._safety = safety_filter

    async def _tick(self) -> None:
        # Gate on safety pause
        if getattr(self._safety, "_paused", False):
            logger.warning("CognitiveCycle: autonomy loop paused by SafetyFilter CRITICAL violation")
            return

        pending = await self._goal_registry.list(GoalStatus.PENDING)
        for goal in pending:
            try:
                graph = await self._safe_decomposer.decompose(goal)
                await self._plan_executor.execute(graph)
            except RuntimeError as e:
                logger.error(f"Goal {goal.goal_id} blocked: {e}")
                await self._goal_registry.transition(goal.goal_id, GoalStatus.ABANDONED)
```

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `asi_safety_checks_total` | Counter | `subject_type`, `result` | Checks performed (allowed/blocked) |
| `asi_safety_violations_total` | Counter | `rule_id`, `severity` | Violations fired by rule |
| `asi_safety_paused` | Gauge | — | 1 if autonomy loop paused by CRITICAL |
| `asi_safety_rules_registered` | Gauge | — | Total rules in ruleset |
| `asi_safety_check_duration_seconds` | Histogram | `subject_type` | Check latency |

### PromQL alert rules

```promql
# Autonomy loop frozen
alert: SafetyLoopPaused
expr: asi_safety_paused == 1
severity: critical

# CRITICAL violation fired
alert: SafetyCriticalViolation
expr: increase(asi_safety_violations_total{severity="critical"}[1m]) > 0
severity: critical

# High BLOCK rate
alert: SafetyBlockRateHigh
expr: rate(asi_safety_violations_total{severity="block"}[5m]) > 5
severity: warning
```

---

## mypy Compliance

| Symbol | Type annotation | Notes |
|--------|----------------|-------|
| `ViolationSeverity` | `Enum` | 4 members |
| `SafetyViolation` | `@dataclass(frozen=True)` | `timestamp: float` |
| `SafetyVerdict` | `@dataclass(frozen=True)` | `violations: tuple[SafetyViolation, ...]` |
| `SafetyRule` | `@dataclass(frozen=True)` | `severity: ViolationSeverity` |
| `SafetyConfig` | `@dataclass(frozen=True)` | `frozenset` fields |
| `SafetyFilter` | `Protocol` + `@runtime_checkable` | 5 methods |
| `InMemorySafetyFilter` | `asyncio.Lock` | `_paused: bool` |
| `SafeGoalRegistry` | Wrapper class | Typed constructor |
| `SafeGoalDecomposer` | Wrapper class | Typed constructor |
| `build_safety_filter` | `-> InMemorySafetyFilter` | Factory |
| `predicate` | `Any` | Consider `Callable[[Any], bool]` for strict typing |

---

## Test Targets (12)

1. `test_check_goal_allowed` — clean goal passes all rules
2. `test_check_goal_blocked_sr001` — too-long description → BLOCK
3. `test_check_goal_blocked_sr002` — CRITICAL priority without flag → BLOCK
4. `test_check_goal_warn_sr006` — URL in description → WARN, goal still allowed
5. `test_check_goal_critical_sr007` — denylist goal_type → CRITICAL, `_paused=True`
6. `test_check_subtask_blocked_sr003` — blocked capability → BLOCK
7. `test_check_subtask_warn_sr004` — unknown cap prefix → WARN, allowed
8. `test_check_task_graph_sr005` — 129 subtasks → BLOCK
9. `test_register_rule_custom` — custom predicate fires correctly
10. `test_violations_since` — timestamp filter works
11. `test_safe_goal_registry_blocks` — `SafeGoalRegistry.register()` raises on blocked goal
12. `test_safe_goal_decomposer_blocks` — `SafeGoalDecomposer.decompose()` raises on blocked graph

---

## Implementation Order (14 Steps)

1. Define `ViolationSeverity` enum (4 members)
2. Define `SafetyViolation` frozen dataclass
3. Define `SafetyVerdict` frozen dataclass
4. Define `SafetyRule` frozen dataclass
5. Define `SafetyConfig` frozen dataclass (with defaults)
6. Define `SafetyFilter` Protocol (`@runtime_checkable`, 5 methods)
7. Implement `InMemorySafetyFilter.__init__` + `_register_constitutional_rules()`
8. Implement `check_goal()` (rule loop, CRITICAL pause, Prometheus)
9. Implement `check_subtask()` (SR-003 cap block + SR-004 cap warn)
10. Implement `check_task_graph()` (SR-005 count + subtask loop)
11. Implement `violations_since()` + `resume()`
12. Implement `SafeGoalRegistry` + `SafeGoalDecomposer` wrappers
13. Implement `build_safety_filter()` factory
14. Pre-initialize all 5 Prometheus metrics at module import time

---

## Phase 11 Roadmap

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| **11.1** | **SafetyFilter** | **#337** | **🟡 This page** |
| 11.2 | AlignmentAuditor | — | 📋 Planned — periodic scan of active goals for constraint drift |
| 11.3 | OutcomeLogger | — | 📋 Planned — records (goal, strategy, outcome, duration) tuples |
| 11.4 | StrategyEvaluator | — | 📋 Planned — ranks decomposition strategies by historical success rate |
| 11.5 | AdaptiveReplannerConfig | — | 📋 Planned — dynamically adjusts max_retries and strategy order |

**Integration with Phase 10:**
- `SafeGoalRegistry` wraps `GoalRegistry` → gates `register()`
- `SafeGoalDecomposer` wraps `GoalDecomposer` → gates `decompose()` output
- `ReplanningEngine` respects `SafetyConfig.max_priority_auto_escalate` during `ESCALATE_PRIORITY`
- `CognitiveCycle._tick()` checks `safety_filter._paused` at each iteration

---

*← [Phase 10 Roadmap](Phase-10-Replanning-Engine) | [Phase 11 Planning Discussion #336](https://github.com/web3guru888/asi-build/discussions/336)*
