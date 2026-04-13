# ConsciousnessPlanner — Phase 5.4

**Status**: Design | **Issue**: [#194](https://github.com/web3guru888/asi-build/issues/194) | **Discussion**: [#206](https://github.com/web3guru888/asi-build/discussions/206)

`ConsciousnessPlanner` is the Phase 5.4 component that closes the loop between ASI:BUILD's consciousness measurement (IIT Φ, GWT broadcast) and its goal planning stack. When global workspace theory reports a high-Φ conscious state, `ConsciousnessPlanner` adjusts goal priorities to pursue goals consistent with the dominant conscious content.

---

## Position in the CognitiveCycle

```
Tier 4: CONSCIOUSNESS
  ├── ConsciousnessOrchestrator  (runs IIT Φ, GWT, AST, HOT)
  ├── GWTInferenceBridge         ← NEW (Phase 5.4) — translates GWT broadcast to goal signals
  └── ConsciousnessPlanner       ← NEW (Phase 5.4) — applies Φ-weighted goal re-prioritization
```

`ConsciousnessOrchestrator` runs first and writes its output to:
- `consciousness.iit.phi` — current Φ value
- `consciousness.gwt.broadcast_content` — the winning GWT "coalition" (set of modules with attention)
- `consciousness.gwt.broadcast_confidence` — GWT coalition confidence score

`GWTInferenceBridge` reads these entries and writes:
- `consciousness.goal_signals` — list of `GoalSignal(topic, priority_delta, source_phi)`

`ConsciousnessPlanner` reads `consciousness.goal_signals` and applies priority adjustments to the `GoalManager`.

---

## `GWTInferenceBridge`

```python
class GWTInferenceBridge(OnlineLearningAdapter):
    trigger_mode = "event"
    event_topic = "GWT_BROADCAST"

    async def compute_update(self, blackboard_snapshot: dict) -> WeightDelta | None:
        phi = blackboard_snapshot.get("consciousness.iit.phi", 0.0)
        broadcast = blackboard_snapshot.get("consciousness.gwt.broadcast_content", {})
        confidence = blackboard_snapshot.get("consciousness.gwt.broadcast_confidence", 0.0)
        
        if phi < PHI_PLANNING_THRESHOLD:  # default: 0.3
            return None  # below threshold — no planning signal
        
        goal_signals = self._extract_goal_signals(broadcast, phi, confidence)
        if not goal_signals:
            return None
        
        return WeightDelta(
            source_module="gwt_inference_bridge",
            parameter_path="consciousness.goal_signals",
            delta=goal_signals,
            confidence=confidence,
            metadata={"phi": phi, "broadcast_modules": list(broadcast.keys())}
        )
    
    async def apply_update(self, delta: WeightDelta) -> None:
        self.blackboard.write(
            "consciousness.goal_signals",
            delta.delta,
            ttl=10,  # goal signals expire after 10 ticks if not consumed
            metadata=delta.metadata
        )
    
    def _extract_goal_signals(self, broadcast: dict, phi: float, conf: float) -> list[GoalSignal]:
        signals = []
        for module_name, attention_weight in broadcast.items():
            topic = MODULE_TO_GOAL_TOPIC.get(module_name)
            if topic and attention_weight > 0.5:
                signals.append(GoalSignal(
                    topic=topic,
                    priority_delta=phi * attention_weight,
                    source_phi=phi,
                    source_module=module_name
                ))
        return signals
```

`MODULE_TO_GOAL_TOPIC` maps GWT module names to `GoalManager` topic strings:
```python
MODULE_TO_GOAL_TOPIC = {
    "knowledge_graph": "KNOWLEDGE_ACQUISITION",
    "hybrid_reasoning": "INFERENCE",
    "bio_inspired": "HOMEOSTASIS",
    "safety": "SAFETY_VERIFICATION",
    ...
}
```

---

## `ConsciousnessPlanner`

```python
class ConsciousnessPlanner:
    PHI_PLANNING_THRESHOLD = 0.3
    MAX_PRIORITY_BOOST = 2.0      # cap on Φ-weighted boost to any goal
    BOOST_DECAY_RATE = 0.95       # priority boost decays each tick

    def __init__(self, goal_manager: GoalManager, blackboard: CognitiveBlackboard):
        self.goal_manager = goal_manager
        self.blackboard = blackboard
        self._active_boosts: dict[str, float] = {}  # topic → current boost

    async def on_tick(self) -> None:
        signals = self.blackboard.read("consciousness.goal_signals") or []
        phi = self.blackboard.read("consciousness.iit.phi") or 0.0
        
        # Apply new signals
        for signal in signals:
            boost = min(signal.priority_delta, self.MAX_PRIORITY_BOOST)
            self._active_boosts[signal.topic] = max(
                self._active_boosts.get(signal.topic, 0.0), boost
            )
        
        # Apply boosts to GoalManager
        for topic, boost in list(self._active_boosts.items()):
            self.goal_manager.boost_priority(topic, boost)
            self._active_boosts[topic] *= self.BOOST_DECAY_RATE
            if self._active_boosts[topic] < 0.01:
                del self._active_boosts[topic]
        
        # Write planning state to Blackboard for metrics
        self.blackboard.write("consciousness.planner.active_boosts", dict(self._active_boosts))
        self.blackboard.write("consciousness.planner.phi", phi)
```

The exponential decay (`BOOST_DECAY_RATE = 0.95`) ensures that a one-time high-Φ event gradually releases control of the goal queue, rather than permanently boosting a topic.

---

## Safety invariants

From [Phase 5 Safety Invariants](Phase-5-Safety-Invariants):

1. **Φ threshold gate**: `GWTInferenceBridge.compute_update()` returns `None` when `Φ < PHI_PLANNING_THRESHOLD`. No goal signals are generated for low-consciousness states.
2. **Priority boost cap**: `MAX_PRIORITY_BOOST = 2.0` prevents consciousness from completely overriding the baseline goal queue.
3. **Safety topic immunity**: The `SAFETY_VERIFICATION` topic is excluded from `MAX_PRIORITY_BOOST` capping — safety goals can always be boosted to maximum priority.
4. **SLEEP_PHASE exclusion**: `ConsciousnessPlanner.on_tick()` is skipped during `SLEEP_PHASE`.

---

## Blackboard entries written

| Key | Type | TTL | Description |
|---|---|---|---|
| `consciousness.goal_signals` | `list[GoalSignal]` | 10 ticks | GWT → planner signals |
| `consciousness.planner.active_boosts` | `dict[str, float]` | 5 ticks | Current boost state |
| `consciousness.planner.phi` | `float` | 5 ticks | Φ at time of planning |

---

## Metrics

Collected by `Phase5MetricsCollector` ([Phase-5-Evaluation](Phase-5-Evaluation)):

| Metric | Definition | Target |
|---|---|---|
| `phi_weighted_goal_acceptance_rate` | Fraction of high-Φ goal signals accepted by GoalManager | > 0.80 |
| `gwt_broadcast_latency_p99` | GWTInferenceBridge → ConsciousnessPlanner update latency | < 50ms |
| `active_boost_count` | Number of goals with active Φ boosts | < 8 |

---

## Related

- [Phase 5 Roadmap](Phase-5-Roadmap)
- [Phase 5 Safety Invariants](Phase-5-Safety-Invariants)
- [Online Learning Adapter](Online-Learning-Adapter)
- [Consciousness Module](Consciousness-Module)
- [Phase-5-Evaluation](Phase-5-Evaluation)
