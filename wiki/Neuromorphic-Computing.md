# Neuromorphic Computing Module

## Overview
- Location: `src/asi_build/neuromorphic/`
- Size: ~5,226 LOC across 4 subdirectories (core, hardware, learning, spiking)
- Status: Research-grade — biologically realistic neuron models, hardware simulation layer

## Architecture
```
neuromorphic/
├── core/           # Configuration, management, event processing, temporal dynamics
│   ├── config.py          (361 LOC) — NeuronConfig, SynapseConfig, NetworkConfig dataclasses
│   ├── manager.py         (527 LOC) — NeuromorphicManager: lifecycle + network orchestration
│   ├── event_processor.py (539 LOC) — EventProcessor: spike event queue + priority dispatch
│   ├── temporal_dynamics.py (589 LOC) — Oscillation tracking, gamma/theta rhythms
│   ├── neural_base.py     (625 LOC) — NeuralBase: abstract neuron interface
│   └── spike_monitor.py   (659 LOC) — SpikeMonitor: population statistics, raster plotting
├── hardware/       # Hardware simulation and memristive devices
│   ├── chip_simulator.py     (507 LOC) — Intel Loihi / IBM TrueNorth style chip simulator
│   └── memristive_device.py  (603 LOC) — ReRAM/PCM memristor device model
├── learning/       # Learning rules
│   └── stdp.py   (446 LOC) — STDP + BCM + homeostatic plasticity
└── spiking/        # Neuron + synapse models and network builders
    (neuron_models, synapse_models, network_builder, population)
```

## Neuron Models

### Leaky Integrate-and-Fire (LIF) — Default
The workhorse of computational neuroscience. Membrane potential V obeys:
```
τ_m · dV/dt = -(V - V_rest) + R·I(t)
```
When V ≥ V_threshold → spike, reset to V_reset, enter refractory period.

Default parameters (from `NeuronConfig`):
```python
tau_membrane = 20ms   # Integration time constant
v_threshold  = -50mV  # Spike threshold  
v_reset      = -70mV  # Post-spike reset
v_rest       = -65mV  # Resting potential
refractory_period = 2ms
```

### Adaptive Exponential IF (AdEx)
Adds adaptation variable w that grows with each spike and decays with τ_w:
```
C·dV/dt = -g_L(V - E_L) + g_L·ΔT·exp((V-V_T)/ΔT) + I - w
τ_w·dw/dt = a(V - E_L) - w
```
Produces: regular spiking, bursting, chattering, fast spiking, irregular spiking — depending on parameters.

### Izhikevich Model
Two-variable system tuned for computational efficiency + biological richness:
```
dv/dt = 0.04v² + 5v + 140 - u + I
du/dt = a(bv - u)
if v ≥ 30mV: v = c, u = u + d
```
Captures 20+ firing patterns with just 4 parameters (a, b, c, d).

### Hodgkin-Huxley
Full conductance-based model with Na⁺, K⁺, and leak channels:
```
C_m·dV/dt = -g_Na·m³h(V-E_Na) - g_K·n⁴(V-E_K) - g_L(V-E_L) + I
```
Biophysically accurate but ~10x slower to simulate than LIF.

## Synaptic Models
| Model | Description |
|-------|-------------|
| `ExponentialSynapse` | Instantaneous rise, exponential decay with time constant τ |
| `AlphaFunctionSynapse` | Smoother rise and fall; models AMPA/GABA kinetics |
| `STDPSynapse` | Weight update triggered by spike timing correlation |

## Learning Rules (learning/stdp.py — 446 LOC)

### Spike-Timing-Dependent Plasticity (STDP)
Hebbian learning where the sign and magnitude of weight change depends on timing:
```
Δw = A⁺ · exp(-Δt/τ⁺)  if Δt > 0  (pre before post → LTP)
Δw = -A⁻ · exp( Δt/τ⁻)  if Δt < 0  (post before pre → LTD)
```
Default: A⁺=0.01, A⁻=0.012, τ⁺=τ⁻=20ms (slight LTD bias for stability).

### BCM (Bienenstock-Cooper-Munro) Rule
Sliding threshold θ_M adjusts based on postsynaptic activity history:
```
Δw ∝ φ(y, θ_M) · x
θ_M adapts so high-activity synapses are depressed, low-activity potentiated
```
Models cortical development and orientation selectivity.

### Homeostatic Plasticity
Keeps average firing rate near `target_rate` (default: 5 Hz) by globally scaling all weights. Operates on a slow timescale (τ=1000ms) to stabilize STDP learning.

## Network Topology
`network_builder.py` provides three topology generators:
- **RandomNetwork**: Erdős–Rényi with connection probability `p` (default: 0.1)
- **SmallWorldNetwork**: Watts-Strogatz — clustered locally, short global path length
- **ScaleFreeNetwork**: Barabási-Albert preferential attachment — power-law degree distribution

```python
from asi_build.neuromorphic.spiking import SpikingNetwork, SmallWorldNetwork

net = SpikingNetwork(
    n_neurons=500,
    inhibitory_fraction=0.2,  # Dale's law: 20% inhibitory
    topology=SmallWorldNetwork(k=10, p_rewire=0.1)
)
```

## Hardware Simulation

### Chip Simulator (chip_simulator.py — 507 LOC)
Models a neuromorphic chip in the style of Intel Loihi / IBM TrueNorth:
- Digital spike representation (1-bit events on a mesh)
- Axon routing table simulation
- Configurable cores with local SRAM weight storage
- Energy estimation per spike event

### Memristive Devices (memristive_device.py — 603 LOC)
Models resistive switching memory (ReRAM/PCM) as analog synaptic weights:
```python
from asi_build.neuromorphic.hardware import MemristiveDevice

device = MemristiveDevice(type="PCM", resistance_high=1e6, resistance_low=1e4)
device.program(target_conductance=0.5)   # Analog weight write
w = device.read_conductance()            # Weight read with noise
```
Includes: device-to-device variation, read/write noise, endurance cycles, conductance drift.

## Temporal Dynamics (core/temporal_dynamics.py — 589 LOC)
Tracks neural oscillations:
- **Gamma (30–80 Hz)**: Attention, feature binding
- **Theta (4–8 Hz)**: Memory encoding, hippocampal-cortical communication
- **Alpha (8–12 Hz)**: Idle/inhibitory rhythms
- **Beta (12–30 Hz)**: Motor control, working memory maintenance

Oscillation phase can modulate spike probability — models phase precession and theta-gamma coupling.

## Spike Monitor (core/spike_monitor.py — 659 LOC)
Records and analyses population activity:
```python
monitor = SpikeMonitor(population_size=500)
monitor.record(spike_times, neuron_ids)

stats = monitor.compute_statistics()
# stats.mean_firing_rate — Hz per neuron
# stats.fano_factor      — spike count variability
# stats.cv_isi           — coefficient of variation of ISI
# stats.synchrony        — pairwise correlation coefficient
```
Supports raster plot export (matplotlib) and ISI histogram.

## Integration with ASI:BUILD

### Cognitive Blackboard
The neuromorphic module's `NeuromorphicManager` can write population statistics to the Blackboard:
```python
blackboard.write("neuromorphic", "population_firing_rate", stats.mean_firing_rate)
blackboard.write("neuromorphic", "network_synchrony", stats.synchrony)
```
See Issue #46 for integrating `CognitiveState` from `bio_inspired` with knowledge graph consolidation.

### Bio-Inspired Module
The [Bio-Inspired module](Bio-Inspired) implements circadian/sleep-wake cycles and neuromodulation at a higher level of abstraction. The neuromorphic module provides the lower-level spiking substrate.

### CognitiveCycle Integration
In the [CognitiveCycle](CognitiveCycle) (Phase 4 roadmap), neuromorphic networks could serve as the sensory encoding layer, converting raw inputs into spike trains that feed the reasoning pipeline.

## Benchmarks
No formal benchmarks run yet. Rough targets:
- LIF single neuron: >100K timesteps/second (pure Python)
- SmallWorldNetwork 500 neurons: ~1K timesteps/second
- Chip simulator: depends on topology; ~500 neurons at 10ms resolution = ~50ms wall-clock per second

## Known Limitations
1. **Pure Python**: No C extension or GPU kernel — simulator is slow for large networks
2. **No GPU support**: Unlike PyTorch-based spiking libs (spikingjelly, Norse), no CUDA path
3. **No direct Blackboard adapter yet** — integration is manual
4. **Memristive devices are single-device models** — no array crossbar simulation yet

## Open Research Questions
1. Can STDP + homeostasis in a SmallWorldNetwork reproduce the cognitive state transitions modeled in `bio_inspired` (alert → drowsy → sleep)?
2. What's the right granularity for mapping CognitiveCycle phases to oscillatory states (gamma during perception, theta during recall)?
3. Can memristive crossbar arrays simulate the weight consolidation that happens during sleep-wake cycles in `bio_inspired`?

## Contributing
- **Good first issue**: Add a benchmark script comparing LIF vs AdEx simulation speed
- **Medium**: Wrap CUDA-based `spikingjelly` as an optional backend
- **Hard**: Implement a memristive crossbar array and connect it to the STDP learning rule

## Related Modules
- [Bio-Inspired](Bio-Inspired) — higher-level cognitive state machine + neuromodulation
- [Quantum Computing](Quantum-Computing) — quantum gates share temporal/probabilistic dynamics
- [Consciousness](Consciousness-Module) — IIT Φ can be computed over spiking network connectivity
- [CognitiveCycle](CognitiveCycle) — neuromorphic could serve as the sensory encoding layer
