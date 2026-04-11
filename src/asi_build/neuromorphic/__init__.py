"""
Neuromorphic Computing System for Kenny AI

A comprehensive brain-inspired computing framework that implements:
- Spiking Neural Networks (SNNs)
- Event-driven processing
- Neuromorphic hardware simulation
- STDP learning rules
- Reservoir computing
- Liquid state machines
- Neuromorphic vision systems
- Brain-computer interfaces
- Neural coding schemes
- Neuromorphic robotics control

This module provides the foundation for biologically-inspired AI that mimics
the temporal dynamics and energy efficiency of biological neural systems.
"""

__version__ = "1.0.0"
__author__ = "Kenny AI - Neuromorphic Computing Specialist NC1"

# Core imports
from .core import (
    NeuromorphicConfig,
    NeuromorphicManager,
    EventProcessor,
    TemporalDynamics
)

# Spiking neural network components
from .spiking import (
    SpikingNeuron,
    SpikingNetwork,
    SynapticConnection,
    NeuronModels
)

# Hardware simulation
from .hardware import (
    NeuromorphicChip,
    MemristiveDevice,
    SynapticArray,
    HardwareSimulator
)

# Learning algorithms
from .learning import (
    STDPLearning,
    HomeostasticPlasticity,
    MetaplasticityLearning,
    TemporalLearning
)

# Reservoir computing
from .reservoir import (
    LiquidStateMachine,
    EchoStateNetwork,
    ReservoirComputer,
    DynamicReservoir
)

# Vision processing
from .vision import (
    DVSProcessor,
    SpikeBasedVision,
    TemporalContrast,
    EventBasedTracking
)

# Brain-computer interfaces
from .bci import (
    SpikeDecoder,
    MotorIntention,
    BrainSignalProcessor,
    NeuroprostheticControl
)

# Neural coding
from .coding import (
    RateCodec,
    TemporalCodec,
    PopulationCodec,
    SparseCodec
)

# Robotics control
from .robotics import (
    NeuromorphicController,
    SensoriMotorMapper,
    AdaptiveBehavior,
    EmbodiedLearning
)

__all__ = [
    # Core
    'NeuromorphicConfig',
    'NeuromorphicManager', 
    'EventProcessor',
    'TemporalDynamics',
    
    # Spiking networks
    'SpikingNeuron',
    'SpikingNetwork',
    'SynapticConnection',
    'NeuronModels',
    
    # Hardware
    'NeuromorphicChip',
    'MemristiveDevice',
    'SynapticArray',
    'HardwareSimulator',
    
    # Learning
    'STDPLearning',
    'HomeostasticPlasticity',
    'MetaplasticityLearning',
    'TemporalLearning',
    
    # Reservoir
    'LiquidStateMachine',
    'EchoStateNetwork',
    'ReservoirComputer',
    'DynamicReservoir',
    
    # Vision
    'DVSProcessor',
    'SpikeBasedVision',
    'TemporalContrast',
    'EventBasedTracking',
    
    # BCI
    'SpikeDecoder',
    'MotorIntention',
    'BrainSignalProcessor',
    'NeuroprostheticControl',
    
    # Coding
    'RateCodec',
    'TemporalCodec',
    'PopulationCodec',
    'SparseCodec',
    
    # Robotics
    'NeuromorphicController',
    'SensoriMotorMapper',
    'AdaptiveBehavior',
    'EmbodiedLearning'
]