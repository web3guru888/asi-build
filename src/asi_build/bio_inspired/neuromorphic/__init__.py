"""
Neuromorphic Computing Module

Implements biologically-inspired spiking neural networks and neuromorphic processors
that mimic the temporal dynamics and energy efficiency of biological neurons.
"""

from .spiking_networks import SpikingNeuralNetwork, SpikingNeuron, SynapticConnection
from .neuromorphic_processor import NeuromorphicProcessor, NeuromorphicChip

try:
    from .temporal_coding import TemporalCoding, SpikeTrainAnalyzer
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
    "SpikeEvent"
]