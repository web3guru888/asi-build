# Neuromorphic

> **Maturity**: `experimental` · **Adapter**: `NeuromorphicBlackboardAdapter`

Neuromorphic computing framework simulating brain-inspired hardware and spiking neural networks. Organized into 9 sub-packages covering the full neuromorphic stack: core management and event processing, spiking neuron models (LIF, Izhikevich), hardware simulation (neuromorphic chips, memristive devices, synaptic arrays), learning rules (STDP, homeostatic plasticity, metaplasticity, temporal learning), reservoir computing (liquid state machines, echo state networks), event-driven vision (DVS processing, spike-based vision, temporal contrast), BCI decoding (spike decoding, motor intention), neural coding (rate, temporal, population, sparse codecs), and neuromorphic robotics (sensorimotor mapping, adaptive behavior).

Up to 36 classes exported dynamically via fault-tolerant imports.

## Key Classes

| Class | Description |
|-------|-------------|
| `NeuromorphicManager` | Core manager for neuromorphic system lifecycle |
| `NeuromorphicConfig` | Configuration dataclass for neuromorphic parameters |
| `EventProcessor` | Processes spike events and temporal dynamics |
| `TemporalDynamics` | Temporal dynamics computation for spiking networks |
| `SpikingNeuron` | Individual spiking neuron model (LIF, Izhikevich) |
| `SpikingNetwork` | Network of interconnected spiking neurons |
| `SynapticConnection` | Weighted synaptic connection between neurons |
| `NeuromorphicChip` | Simulated neuromorphic hardware chip |
| `MemristiveDevice` | Memristive device simulation for analog weights |
| `SynapticArray` | Crossbar array of synaptic devices |
| `HardwareSimulator` | Full hardware simulation environment |
| `STDPLearning` | Spike-Timing-Dependent Plasticity learning rule |
| `HomeostasticPlasticity` | Homeostatic plasticity for activity regulation |
| `MetaplasticityLearning` | Metaplasticity (plasticity of plasticity) |
| `LiquidStateMachine` | Reservoir computing via liquid state machines |
| `EchoStateNetwork` | Echo state network for temporal pattern learning |
| `ReservoirComputer` | General reservoir computing framework |
| `DVSProcessor` | Dynamic Vision Sensor event stream processor |
| `SpikeBasedVision` | Spike-based visual processing pipeline |
| `EventBasedTracking` | Event-driven object tracking |
| `SpikeDecoder` | Neural spike train decoder for BCI |
| `MotorIntention` | Motor intention decoding from neural signals |
| `NeuroprostheticControl` | Neuroprosthetic device control interface |
| `RateCodec` | Rate coding encoder/decoder |
| `TemporalCodec` | Temporal coding encoder/decoder |
| `PopulationCodec` | Population coding encoder/decoder |
| `SparseCodec` | Sparse coding encoder/decoder |
| `NeuromorphicController` | High-level neuromorphic robotics controller |
| `SensoriMotorMapper` | Sensorimotor mapping for embodied agents |
| `AdaptiveBehavior` | Adaptive behavior generation |
| `EmbodiedLearning` | Learning through embodied interaction |

## Example Usage

```python
from asi_build.neuromorphic import SpikingNetwork, STDPLearning, NeuromorphicConfig
config = NeuromorphicConfig(dt=0.001, num_neurons=100)
network = SpikingNetwork(config=config)
stdp = STDPLearning(a_plus=0.01, a_minus=0.012, tau=20.0)
network.set_learning_rule(stdp)
network.simulate(steps=1000, input_spikes=spike_train)
```

## Blackboard Integration

NeuromorphicBlackboardAdapter publishes spike patterns, network state, learning progress, and hardware utilization; consumes sensory inputs and BCI signals for event-driven processing.
