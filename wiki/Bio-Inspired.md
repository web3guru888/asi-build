# Bio-Inspired Cognitive Architecture

The `bio_inspired` module is one of ASI:BUILD's most biologically grounded components — a full cognitive architecture modelled on the principles of biological intelligence as articulated in Ben Goertzel's research. Rather than treating neuroscience as a metaphor, it attempts to implement the actual computational mechanisms that biological brains use: circadian rhythms, neuromodulation, sleep-dependent memory consolidation, STDP learning rules, and more.

---

## Architecture Overview

```
BioCognitiveArchitecture (core.py)
├── NeuromorphicProcessor        ← spiking neural networks
├── EvolutionaryOptimizer        ← genetic programming
├── HomeostaticRegulator         ← allostasis + setpoint control
├── DevelopmentalLearning        ← stage-based cognitive growth
├── NeuromodulationSystem        ← dopamine / serotonin / NE / ACh
├── SleepWakeCycle               ← NREM + REM + consolidation
├── EmotionalRegulation          ← affective computing
├── EmbodiedCognition            ← sensorimotor integration
├── NeuroplasticityManager       ← STDP + BCM + synaptic pruning
├── HierarchicalTemporalMemory   ← HTM sequences
├── BiologicalLearning (STDP/BCM)← learning rules
└── EnergyMetrics                ← metabolic cost tracking
```

The `BioCognitiveArchitecture` orchestrator manages all of these as pluggable `BioCognitiveModule` instances, running them concurrently via `asyncio`.

---

## Cognitive States

The system transitions between 8 states driven by a circadian clock and sleep-pressure accumulator:

| State | Description |
|-------|-------------|
| `AWAKE_ACTIVE` | Full attention and learning capacity |
| `AWAKE_RESTING` | Reduced arousal, mild consolidation |
| `NREM_SLEEP` | Deep sleep — strongest memory consolidation |
| `REM_SLEEP` | Dreaming phase — emotional processing, pattern replay |
| `LEARNING` | Explicit learning mode — high plasticity |
| `CONSOLIDATING` | Active memory consolidation |
| `DEVELOPING` | Developmental stage transition |
| `ADAPTING` | Rapid homeostatic adjustment |

State transitions use a **sleep pressure model** (adenosine-inspired): pressure builds during waking, dissipates during sleep. The circadian phase adds a sinusoidal modifier so even a rested system will feel "sleepy" at the wrong time of day.

```python
sleep_drive = self.sleep_pressure + 0.5 * np.sin(2 * np.pi * self.circadian_clock)
```

---

## BiologicalMetrics

Every module exposes a `BiologicalMetrics` dataclass:

```python
@dataclass
class BiologicalMetrics:
    energy_efficiency: float      # 0–1, metabolic cost ratio
    spike_rate: float             # Hz equivalent
    synaptic_strength: float      # mean weight magnitude
    plasticity_index: float       # recent LTP/LTD rate
    homeostatic_balance: float    # distance from setpoint
    developmental_stage: float    # 0 (infant) → 1 (mature)
    emotional_valence: float      # -1 (negative) → +1 (positive)
    attention_focus: float        # 0 (diffuse) → 1 (focused)
    memory_consolidation: float   # recent consolidation activity
    neurotransmitter_levels: Dict[str, float]  # named NT levels
```

These metrics propagate upward to the `global_metrics` object on the orchestrator, giving a system-wide view of biological state.

---

## Neuromodulation

The `NeuromodulationSystem` tracks four classical neurotransmitters with configurable baselines:

| NT | Default baseline | Primary effect |
|----|-----------------|----------------|
| Dopamine | 0.3 | Reward prediction, motivation, learning gate |
| Serotonin | 0.4 | Mood regulation, satiety, sleep preparation |
| Norepinephrine | 0.2 | Arousal, attention, fight-or-flight |
| Acetylcholine | 0.5 | Memory encoding, attention sharpening |

These modulate the **learning rates, attention weights, and plasticity thresholds** of other modules. High dopamine → stronger LTP. High NE → tighter attention focus. Low serotonin → emotional dysregulation during the `EmotionalRegulation` module's processing.

---

## Learning Rules

### STDP (Spike-Timing Dependent Plasticity)

```python
# Potentiation: pre fires before post (causal)
Δw = A_plus * exp(-Δt / τ_plus)  if Δt > 0

# Depression: post fires before pre (anti-causal)  
Δw = -A_minus * exp(Δt / τ_minus)  if Δt < 0
```

The default STDP window is 20ms, matching biological measurements from cortical neurons. LTP triggers above 0.6 synaptic correlation; LTD below 0.3.

### BCM (Bienenstock-Cooper-Munro)

The BCM rule adds a **sliding threshold** `θ_M` that adjusts based on the neuron's recent average activity. If a neuron fires too often, its threshold rises (metaplasticity), preventing runaway potentiation:

```
Δw ∝ y(y - θ_M) * x
```

This implements **synaptic homeostasis** at the individual neuron level.

---

## Developmental Learning

`DevelopmentalLearning` models cognitive growth through stages analogous to Piaget's developmental theory:

| Stage | `developmental_stage` | Characteristics |
|-------|----------------------|-----------------|
| Infant | 0.0–0.2 | High plasticity, broad generalization |
| Child | 0.2–0.5 | Category formation, rapid vocabulary |
| Adolescent | 0.5–0.8 | Abstract reasoning, pruning begins |
| Adult | 0.8–1.0 | Specialization, lower baseline plasticity |

The `growth_factor` (default 1.2) controls how quickly the system advances through stages based on accumulated learning signal.

---

## Sleep-Wake Cycle and Memory Consolidation

The `SleepWakeCycle` component drives memory consolidation during sleep phases:

- **NREM sleep** (80% probability when sleep drive > threshold): strongest consolidation weight (1.0). Episodic → semantic transfer.
- **REM sleep** (20% probability): emotional memory processing, pattern replay, creative recombination.
- **Consolidation strength** (default 0.6): scales how much recent experience is replayed and reinforced.

This mirrors the **two-stage memory model** in neuroscience: fast hippocampal encoding during wake, slow cortical consolidation during sleep.

---

## Homeostatic Regulation

`HomeostaticRegulator` maintains four setpoints:

```python
homeostatic_targets = {
    "energy":    0.7,  # metabolic reserve
    "arousal":   0.5,  # alertness level
    "valence":   0.0,  # emotional baseline (neutral)
    "attention": 0.6,  # default focus level
}
```

The regulation strength (default 0.1) and adaptation rate (0.01) control how aggressively the system corrects deviations — analogous to the autonomic nervous system's role in maintaining physiological balance.

---

## Energy Efficiency

The `EnergyMetrics` / `BiologicalEfficiencyComparator` subsystem tracks metabolic cost:

- Each spike costs `spike_cost` (default 0.001) units of energy
- `target_efficiency` (default 0.8): the desired ratio of computation per energy unit
- `metabolic_cost_weight` (default 0.2): trade-off factor in the fitness function for evolutionary optimization

Comparing ASI:BUILD's energy profile against biological benchmarks (e.g., 20W human brain) is one of the open research directions.

---

## Configuration Reference

Full default config (all values are tunable via the constructor):

```python
config = {
    "neuromorphic": {
        "num_neurons": 10000,
        "connection_probability": 0.1,
        "spike_threshold": -55.0,      # mV equivalent
        "refractory_period": 2.0,      # ms
    },
    "evolutionary": {
        "population_size": 100,
        "mutation_rate": 0.01,
        "crossover_rate": 0.8,
        "selection_pressure": 0.2,
    },
    "homeostatic": {
        "regulation_strength": 0.1,
        "adaptation_rate": 0.01,
        "setpoint_flexibility": 0.05,
    },
    "developmental": {
        "maturation_rate": 0.001,
        "pruning_threshold": 0.1,
        "growth_factor": 1.2,
    },
    "neuromodulation": {
        "dopamine_baseline": 0.3,
        "serotonin_baseline": 0.4,
        "norepinephrine_baseline": 0.2,
        "acetylcholine_baseline": 0.5,
    },
    "sleep_wake": {
        "sleep_threshold": 0.8,
        "wake_threshold": 0.2,
        "consolidation_strength": 0.6,
    },
    "neuroplasticity": {
        "stdp_window": 20.0,    # ms
        "ltp_threshold": 0.6,
        "ltd_threshold": 0.3,
        "metaplasticity_rate": 0.01,
    },
    "energy_efficiency": {
        "target_efficiency": 0.8,
        "metabolic_cost_weight": 0.2,
        "spike_cost": 0.001,
    },
}
```

---

## Usage Example

```python
import asyncio
from asi_build.bio_inspired import BioCognitiveArchitecture

# Initialize with custom config
arch = BioCognitiveArchitecture(config={
    "neuromodulation": {
        "dopamine_baseline": 0.5,  # higher reward sensitivity
        "serotonin_baseline": 0.3,
    }
})

# Process a sensory input
result = asyncio.run(arch.process_input({
    "visual": {"edges": [...], "colors": [...]},
    "proprioception": {"joint_angles": [...]},
}))

print(result["state"])           # "awake_active"
print(result["metrics"])         # BiologicalMetrics dict
print(result["processing_time"]) # seconds
```

---

## CognitiveCycle Integration

Within the 9-phase `CognitiveCycle`, `BioCognitiveArchitecture` participates in multiple phases:

| CognitiveCycle Phase | Bio-Inspired Role |
|---------------------|------------------|
| Phase 1: Sensory Preprocessing | Provides proprioception + embodied perception |
| Phase 4: Affect & Drive | `EmotionalRegulation` + neuromodulator state |
| Phase 6: Memory Consolidation | `SleepWakeCycle.consolidate()` called if in NREM |
| Phase 9: Homeostatic Update | `HomeostaticRegulator.update()` after each tick |

See [CognitiveCycle](CognitiveCycle) for the full integration design.

---

## Open Research Questions

1. **Calibrating sleep pressure**: The current accumulator is linear (`+0.0001` per tick). Real adenosine dynamics are more complex — nonlinear, glymphatic clearance during deep sleep. Should we model this more faithfully?

2. **STDP vs. backpropagation**: STDP is biologically plausible but slower to converge than gradient descent. When does biological plausibility cost too much performance? Is there a hybrid (e.g., contrastive Hebbian learning) that preserves biological realism?

3. **Neuromodulator coupling**: In biology, dopamine and serotonin interact (serotonin suppresses dopaminergic VTA firing). Should the `NeuromodulationSystem` model these cross-NT interactions?

4. **Energy accounting**: Is 0.001 energy units per spike a meaningful abstraction, or does it need grounding in actual FLOP counts or joules? How do we benchmark against the 20W human brain?

5. **Emotional valence grounding**: `emotional_valence` is a float on [-1, +1], but in biology emotions are high-dimensional and embodied. What's the right abstraction for an AGI system?

---

## Known Limitations

| Limitation | Status |
|-----------|--------|
| Spiking networks are float-approximation (not true spike trains) | Partial — neuromorphic submodule planned |
| BCM threshold update not implemented in current core.py | Open — would need sliding θ_M integration |
| Sleep-state transitions don't persist across `BioCognitiveArchitecture` restarts | Known gap — no checkpoint/restore |
| Emotional regulation lacks valence-to-action coupling | Research gap |
| No actual developmental stage persistence (resets on init) | Known gap |

---

## Related Pages

- [Architecture](Architecture) — overall system layering
- [CognitiveCycle](CognitiveCycle) — how bio_inspired fits into the full loop
- [Consciousness-Module](Consciousness-Module) — bio_inspired vs. formal consciousness theories
- [Module-Index](Module-Index) — all 29 modules at a glance
