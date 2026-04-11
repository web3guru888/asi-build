"""
Spiking Neural Network Components

Implements various spiking neuron models and network architectures:
- Leaky Integrate-and-Fire neurons
- Adaptive Exponential IF neurons  
- Izhikevich neurons
- Hodgkin-Huxley neurons
- Synaptic connection models
- Network topology generators
"""

_names = {}

try:
    from .neuron_models import (
        LeakyIntegrateFireNeuron,
        AdaptiveExponentialIF,
        IzhikevichNeuron,
        HodgkinHuxleyNeuron,
        SpikingNeuron
    )
    _names.update({k: v for k, v in locals().items() if not k.startswith('_')})
except (ImportError, ModuleNotFoundError):
    pass

try:
    from .synapse_models import (
        ExponentialSynapse,
        AlphaFunctionSynapse,
        STDPSynapse,
        SynapticConnection
    )
    _names.update({k: v for k, v in locals().items() if not k.startswith('_')})
except (ImportError, ModuleNotFoundError):
    pass

try:
    from .network_builder import (
        SpikingNetwork,
        NetworkTopology,
        RandomNetwork,
        SmallWorldNetwork,
        ScaleFreeNetwork
    )
    _names.update({k: v for k, v in locals().items() if not k.startswith('_')})
except (ImportError, ModuleNotFoundError):
    pass

try:
    from .population import (
        NeuronPopulation,
        PopulationConnector,
        PopulationEncoder
    )
    _names.update({k: v for k, v in locals().items() if not k.startswith('_')})
except (ImportError, ModuleNotFoundError):
    pass

__all__ = list(_names.keys())
