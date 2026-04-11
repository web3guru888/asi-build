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


def _try_import(module_path, names):
    """Attempt to import names from a submodule, silently skip on failure."""
    result = {}
    try:
        import importlib
        mod = importlib.import_module(module_path, package=__name__)
        for name in names:
            val = getattr(mod, name, None)
            if val is not None:
                result[name] = val
    except (ImportError, ModuleNotFoundError, SyntaxError):
        pass
    return result


_all_imports = {}

# Core imports
_all_imports.update(_try_import('.core', [
    'NeuromorphicConfig', 'NeuromorphicManager', 'EventProcessor', 'TemporalDynamics'
]))

# Spiking neural network components
_all_imports.update(_try_import('.spiking', [
    'SpikingNeuron', 'SpikingNetwork', 'SynapticConnection', 'NeuronModels'
]))

# Hardware simulation
_all_imports.update(_try_import('.hardware', [
    'NeuromorphicChip', 'MemristiveDevice', 'SynapticArray', 'HardwareSimulator'
]))

# Learning algorithms
_all_imports.update(_try_import('.learning', [
    'STDPLearning', 'HomeostasticPlasticity', 'MetaplasticityLearning', 'TemporalLearning'
]))

# Reservoir computing
_all_imports.update(_try_import('.reservoir', [
    'LiquidStateMachine', 'EchoStateNetwork', 'ReservoirComputer', 'DynamicReservoir'
]))

# Vision processing
_all_imports.update(_try_import('.vision', [
    'DVSProcessor', 'SpikeBasedVision', 'TemporalContrast', 'EventBasedTracking'
]))

# Brain-computer interfaces
_all_imports.update(_try_import('.bci', [
    'SpikeDecoder', 'MotorIntention', 'BrainSignalProcessor', 'NeuroprostheticControl'
]))

# Neural coding
_all_imports.update(_try_import('.coding', [
    'RateCodec', 'TemporalCodec', 'PopulationCodec', 'SparseCodec'
]))

# Robotics control
_all_imports.update(_try_import('.robotics', [
    'NeuromorphicController', 'SensoriMotorMapper', 'AdaptiveBehavior', 'EmbodiedLearning'
]))

globals().update(_all_imports)
__all__ = list(_all_imports.keys())
