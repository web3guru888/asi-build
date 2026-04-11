"""
Neuromorphic Computing Module

Implements biologically-inspired spiking neural networks and neuromorphic processors
that mimic the temporal dynamics and energy efficiency of biological neurons.
"""

try:
    from .spiking_networks import SpikingNeuralNetwork, SpikingNeuron, SynapticConnection
except (ImportError, ModuleNotFoundError, SyntaxError):
    SpikingNeuralNetwork = None
    SpikingNeuron = None
    SynapticConnection = None
try:
    from .neuromorphic_processor import NeuromorphicChip, NeuromorphicProcessor
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuromorphicProcessor = None
    NeuromorphicChip = None

try:
    from .temporal_coding import SpikeTrainAnalyzer, TemporalCoding
except ImportError:
    TemporalCoding = None
    SpikeTrainAnalyzer = None

try:
    from .event_driven import EventDrivenProcessor, SpikeEvent
except ImportError:
    EventDrivenProcessor = None
    SpikeEvent = None

__all__ = [
    "SpikingNeuralNetwork",
    "SpikingNeuron",
    "SynapticConnection",
    "NeuromorphicProcessor",
    "NeuromorphicChip",
    "TemporalCoding",
    "SpikeTrainAnalyzer",
    "EventDrivenProcessor",
    "SpikeEvent",
]
