# Cognitive Synergy Module

> **Path**: `src/asi_build/cognitive_synergy/`  
> **LOC**: 6,314 | **Files**: 12 | **Status**: Stable, no tests yet ([Issue #1](https://github.com/web3guru888/asi-build/issues/1))

The Cognitive Synergy module implements Ben Goertzel's **PRIMUS theory** of cognitive synergy — the idea that general intelligence emerges not from individual modules operating in isolation, but from *synergistic interaction* between cognitive processes. It is the closest thing in ASI:BUILD to a formal theory of mind.

---

## Architecture

```
cognitive_synergy/
├── core/
│   ├── cognitive_synergy_engine.py   # Main orchestrator (616 LOC)
│   ├── emergent_properties.py        # Emergence detection (770 LOC)
│   ├── primus_foundation.py          # PRIMUS framework core (488 LOC)
│   ├── self_organization.py          # Adaptive self-org mechanisms (723 LOC)
│   └── synergy_metrics.py            # Information-theoretic measures (546 LOC)
├── pattern_reasoning/
│   ├── pattern_mining_engine.py      # Multi-level pattern discovery (779 LOC)
│   ├── pattern_reasoning_synergy.py  # Bidirectional pattern↔reasoning (722 LOC)
│   └── reasoning_engine.py           # Logical inference engine (859 LOC)
└── perception_action/
    ├── action_engine.py              # Action selection and execution (37 LOC)
    ├── perception_engine.py          # Sensory processing (35 LOC)
    └── sensorimotor_synergy.py       # Perception↔action coupling (575 LOC)
```

---

## Theoretical Foundation: PRIMUS

The `PRIMUSFoundation` class (`primus_foundation.py`) implements Goertzel's PRIMUS framework as five interacting principles:

| Acronym | Principle | Implementation |
|---------|-----------|----------------|
| **PR** | Pattern Recognition and Information Mining | `PatternMiningEngine` — multi-level pattern discovery |
| **IM** | (**I**nformation **M**ining is part of PRIM) | DBSCAN + PCA clustering, temporal/causal patterns |
| **U** | Understanding and Synthesis | `ReasoningEngine` — 7 reasoning types |
| **S** | Self-Organization and Adaptation | `SelfOrganizationMechanism` — homeostasis + restructuring |
| **MOT** | Motivation and Goal-Oriented Behavior | Goal vector in `PRIMUSState` |
| **INT** | Interaction and Communication | Bidirectional synergy bridges |
| **SOA** | Self-Organization and Adaptation | Entropy + complexity + coherence metrics |

**`PRIMUSState`** — the global cognitive state snapshot:

```python
@dataclass
class PRIMUSState:
    pattern_space: Dict[str, Any]        # Discovered patterns
    understanding_level: float           # 0.0–1.0 synthesis depth
    motivation_vector: np.ndarray        # 10-dim goal representation
    interaction_context: Dict[str, Any]  # Current interaction frame
    self_organization_metrics: Dict[str, float]
    timestamp: float
```

**`CognitivePrimitive`** — the atomic unit:

```python
@dataclass
class CognitivePrimitive:
    name: str
    type: str       # 'pattern', 'concept', 'procedure', 'goal', ...
    content: Any
    confidence: float
    activation: float
    connections: List[str]   # Links to other primitives
    metadata: Dict[str, Any]
```

---

## Core Engine: 10 Synergy Pairs

`CognitiveSynergyEngine` manages **10 fundamental cognitive dualities**, each represented as a `SynergyPair`:

| # | Synergy Pair | Description |
|---|-------------|-------------|
| 1 | **Pattern Mining ↔ Reasoning** | Patterns guide hypotheses; logic guides search |
| 2 | **Perception ↔ Action** | Forward/inverse models + sensorimotor loops |
| 3 | **Memory ↔ Learning** | Consolidation and retrieval interact |
| 4 | **Attention ↔ Intention** | Goals direct attention; salience shapes goals |
| 5 | **Symbolic ↔ Subsymbolic** | Logic meets neural embeddings |
| 6 | **Local ↔ Global** | Feature details vs. holistic context |
| 7 | **Reactive ↔ Deliberative** | Fast reflexes vs. slow planning |
| 8 | **Exploitation ↔ Exploration** | Use known vs. discover new |
| 9 | **Self ↔ Other** | Self-model vs. world model |
| 10 | **Conscious ↔ Unconscious** | Reportable vs. implicit processing |

```python
from asi_build.cognitive_synergy.core.cognitive_synergy_engine import CognitiveSynergyEngine
from asi_build.cognitive_synergy.core.primus_foundation import PRIMUSFoundation

primus = PRIMUSFoundation(dimension=512, learning_rate=0.01)
engine = CognitiveSynergyEngine(
    primus_foundation=primus,
    update_frequency=10.0,     # Hz
    synergy_threshold=0.6,
    emergence_threshold=0.8,
)
```

**`SynergyPair`** dataclass:
```python
@dataclass
class SynergyPair:
    process_a: str
    process_b: str
    synergy_strength: float
    bidirectional_flow: Dict[str, Any]
    integration_level: float
    emergence_indicators: List[str]
    last_updated: float
```

---

## Emergent Properties Detection

`EmergentPropertyDetector` (`emergent_properties.py`, 770 LOC) monitors running synergy and flags **novel behaviors** that arise from cross-process interaction. This is the module's most speculative — and most intellectually interesting — component.

### Detector Hierarchy

```
EmergenceDetector (ABC)
├── BehavioralEmergenceDetector   — novelty threshold on behavior history
├── StructuralEmergenceDetector   — graph-topology change detection
├── FunctionalEmergenceDetector   — capability appearance/disappearance
└── CognitiveEmergenceDetector    — higher-order cognitive pattern emergence
```

### EmergentProperty dataclass
```python
@dataclass
class EmergentProperty:
    id: str
    name: str
    description: str
    emergence_type: str    # 'behavioral' | 'structural' | 'functional' | 'cognitive'
    strength: float        # 0–1
    novelty: float         # 0–1 (how novel vs. known behaviors)
    stability: float       # 0–1 (how persistent)
    complexity: float      # 0–1
    contributing_processes: List[str]
    evidence: List[Dict[str, Any]]
    observation_count: int
```

**DBSCAN** and **PCA** are used to cluster system-state trajectories and identify when the system enters genuinely novel regions of behavior-space. `BehavioralEmergenceDetector` maintains a rolling history and flags states whose novelty score exceeds `0.7`.

---

## Synergy Metrics (Information Theory)

`SynergyMetrics` (`synergy_metrics.py`, 546 LOC) provides a rigorous, information-theoretic basis for measuring how much synergy two cognitive processes actually produce:

| Metric | Method | Meaning |
|--------|--------|---------|
| **Mutual Information** | `sklearn.feature_selection.mutual_info_regression` | Statistical co-dependence |
| **Transfer Entropy** | Custom estimator over discretized state history | Directed causality (X→Y vs Y→X) |
| **Phase Coupling** | `scipy.signal.find_peaks` + Hilbert transform | Temporal synchrony |
| **Coherence** | Spectral coherence over state windows | Functional connectivity |
| **Emergence Index** | Novel state-space region entry rate | Emergence signal |
| **Integration Index** | Synergy − redundancy | True integration vs. overlap |
| **Complexity Resonance** | Σ individual complexities vs. joint complexity | Complexity amplification |

**`SynergyProfile`** — per-pair measurement snapshot:
```python
@dataclass
class SynergyProfile:
    pair_name: str
    mutual_information: float
    transfer_entropy: float
    phase_coupling: float
    coherence: float
    emergence_index: float
    integration_index: float
    complexity_resonance: float
    measurements: List[SynergyMeasurement]
```

---

## Pattern Mining Engine

`PatternMiningEngine` (`pattern_mining_engine.py`, 779 LOC) discovers regularities at multiple abstraction levels:

```
Pattern Levels
├── Low-level sensory patterns    — raw feature correlations
├── Mid-level conceptual patterns — object/event regularities
├── High-level abstract patterns  — relational/causal structures
└── Meta-patterns                 — patterns of patterns
```

**Pattern types**: `sequence`, `spatial`, `temporal`, `structural`, `causal`

**`PatternHierarchy`** — tree of patterns:
```python
@dataclass
class PatternHierarchy:
    root_patterns: List[Pattern]
    sub_patterns: Dict[str, List[Pattern]]     # parent_id → children
    super_patterns: Dict[str, List[Pattern]]   # child_id → parents
    relationships: nx.DiGraph
```

**Algorithms used**: DBSCAN clustering, PCA dimensionality reduction, `StandardScaler` normalization — all from `sklearn`.

---

## Reasoning Engine

`ReasoningEngine` (`reasoning_engine.py`, 859 LOC) performs 7 reasoning types:

| Type | Description |
|------|-------------|
| `DEDUCTIVE` | Valid inference from axioms |
| `INDUCTIVE` | Generalize from examples |
| `ABDUCTIVE` | Best-explanation inference |
| `ANALOGICAL` | Transfer via structural similarity |
| `CAUSAL` | Directed cause-effect chains |
| `TEMPORAL` | Reason over time sequences |
| `SPATIAL` | Spatial relationship inference |

**Core structures**:
```python
@dataclass
class Hypothesis:
    id: str
    content: str
    reasoning_type: ReasoningType
    confidence: float
    evidence: List[str]
    predictions: List[str]
    support_count: int
    refutation_count: int

@dataclass
class Inference:
    id: str
    premises: List[str]
    conclusion: str
    inference_type: ReasoningType
    confidence: float
```

---

## Pattern ↔ Reasoning Synergy

`PatternReasoningSynergy` (`pattern_reasoning_synergy.py`, 722 LOC) implements the **bidirectional bridge** between pattern mining and reasoning — Synergy Pair #1 in the engine:

```
SynergyEvent types:
├── 'pattern_guides_reasoning'   — Pattern → hypothesis seeding
├── 'reasoning_guides_patterns'  — Logic → search space pruning
└── 'mutual_enhancement'         — Co-reinforcement cycle
```

```python
@dataclass
class SynergyEvent:
    event_type: str
    pattern_content: Any
    reasoning_content: Any
    synergy_strength: float
    emergence_level: float
    timestamp: float
```

The `SynergyMetrics` in this module track:
- `bidirectional_flow_rate` — events per second in both directions
- `pattern_to_reasoning_transfer` — unidirectional flow strength P→R
- `reasoning_to_pattern_transfer` — unidirectional flow strength R→P
- `integration_level` — combined integration score

---

## Self-Organization

`SelfOrganizationMechanism` (`self_organization.py`, 723 LOC) keeps the system in a healthy operating regime via three mechanisms:

1. **Homeostatic regulation** — Hold entropy/coherence/efficiency within bounds
2. **Adaptive restructuring** — Modify synergy weights and connections
3. **Resource optimization** — Fair-share across active synergy pairs

**`OrganizationRule`** — rules fire when conditions are met:
```python
@dataclass
class OrganizationRule:
    name: str
    condition: Callable[[Dict], bool]
    action: Callable[[Dict], Dict]
    priority: float
    activation_threshold: float
    cooldown_time: float   # seconds
    effectiveness_history: List[float]
```

**`OrganizationState`** metrics:
- `entropy` — disorder in current configuration
- `complexity` — effective complexity (not just disorder)
- `coherence` — inter-process alignment
- `efficiency` — compute vs. synergy output ratio
- `adaptability` — rate of successful rule application
- `stability` — variance of synergy strengths over time

Uses `scipy.optimize.minimize` for weight optimization and `sklearn.cluster.KMeans` for configuration clustering.

---

## Sensorimotor Synergy

`SensorimotorSynergy` (`sensorimotor_synergy.py`, 575 LOC) closes the perception-action loop:

```python
@dataclass
class SensorimotorLoop:
    name: str
    perception_modality: str
    action_modality: str
    coupling_strength: float
    feedback_delay: float       # seconds (default: 0.1)
    adaptation_rate: float      # default: 0.01
    prediction_accuracy: float
```

Two complementary models:
- **Forward model** — Given action → predict sensory outcome
- **Inverse model** — Given desired outcome → generate action

This implements *active inference* (Friston-style) at a high level — the system acts to minimize prediction error, not just to maximize reward.

---

## Open Questions & Research Directions

This module has some of the deepest open questions in ASI:BUILD:

1. **Synergy measurement validity** — Transfer entropy and mutual information are computed over discretized state histories. Are the discretization choices principled? What bin sizes are appropriate for cognitive state spaces?

2. **Emergence operationalization** — The emergence detection uses novelty thresholds over behavior history. Is this actually measuring *emergence* (causal reduction failure) or just *novelty* (distributional shift)?

3. **PRIMUS faithfulness** — Goertzel's PRIMUS is a high-level theoretical framework. How faithful is this implementation to the mathematical details? Which aspects are solid implementations vs. structural placeholders?

4. **Synergy pair completeness** — Are the 10 synergy pairs the right decomposition? Do they overlap? Are there important dualities missing (e.g., Fast↔Slow, Local↔Global is listed but Fast↔Slow/System 1↔2 is not)?

5. **Grounding** — The module manages internal cognitive dynamics beautifully, but has almost no connection to the Cognitive Blackboard or external inputs. Until it's wired in, synergy happens in isolation. See [Issue #1](https://github.com/web3guru888/asi-build/issues/1) and the [CognitiveCycle](CognitiveCycle) page.

---

## Current Status

| Aspect | Status |
|--------|--------|
| Core engine | ✅ Implemented |
| PRIMUS foundation | ✅ Implemented |
| Emergent property detection | ✅ Implemented |
| Synergy metrics | ✅ Implemented |
| Self-organization | ✅ Implemented |
| Pattern mining + reasoning | ✅ Implemented |
| Sensorimotor synergy | ✅ Implemented |
| Unit tests | ❌ None — **[Good First Issue #1](https://github.com/web3guru888/asi-build/issues/1)** |
| Blackboard integration | ❌ Not wired |
| CognitiveCycle integration | ❌ Pending [Issue #41](https://github.com/web3guru888/asi-build/issues/41) |
| Benchmark suite | ❌ Not yet |

The module has no unit tests — making [Issue #1](https://github.com/web3guru888/asi-build/issues/1) an excellent entry point for new contributors. The interface is clean Python dataclasses; writing property-based tests with Hypothesis would be a great fit.

---

## See Also

- [Architecture](Architecture) — How Cognitive Synergy fits in the layered stack
- [Cognitive Blackboard](Cognitive-Blackboard) — Integration target
- [CognitiveCycle](CognitiveCycle) — Where synergy drives the real-time loop
- [Consciousness Module](Consciousness-Module) — IIT Φ + GWT + AST theories
- [Hybrid Reasoning](Hybrid-Reasoning) — 6 reasoning modes building on the reasoning engine
- [Bio-Inspired](Bio-Inspired) — Biological plausibility complementing synergy
- [Issue #1](https://github.com/web3guru888/asi-build/issues/1) — Add unit tests (good first issue)
