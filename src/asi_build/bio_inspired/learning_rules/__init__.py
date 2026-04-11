"""
Biologically Plausible Learning Rules Module

Implements various biologically plausible learning mechanisms including
STDP, BCM rule, and other synaptic plasticity mechanisms found in biological
neural networks.
"""

try:
    from .stdp_learning import SpikeTimingWindow, STDPLearning, STDPRule
except (ImportError, ModuleNotFoundError, SyntaxError):
    STDPLearning = None
    STDPRule = None
    SpikeTimingWindow = None
try:
    from .bcm_learning import BCMLearning, BCMRule, SlidingThreshold
except (ImportError, ModuleNotFoundError, SyntaxError):
    BCMLearning = None
    BCMRule = None
    SlidingThreshold = None
try:
    from .hebbian_learning import AntiHebbianLearning, HebbianLearning
except (ImportError, ModuleNotFoundError, SyntaxError):
    HebbianLearning = None
    AntiHebbianLearning = None
try:
    from .homeostatic_plasticity import HomeostaticPlasticity, SynapticScaling
except (ImportError, ModuleNotFoundError, SyntaxError):
    HomeostaticPlasticity = None
    SynapticScaling = None
try:
    from .metaplasticity import Metaplasticity, PlasticityModulation
except (ImportError, ModuleNotFoundError, SyntaxError):
    Metaplasticity = None
    PlasticityModulation = None

__all__ = [
    "STDPLearning",
    "STDPRule",
    "SpikeTimingWindow",
    "BCMLearning",
    "BCMRule",
    "SlidingThreshold",
    "HebbianLearning",
    "AntiHebbianLearning",
    "HomeostaticPlasticity",
    "SynapticScaling",
    "Metaplasticity",
    "PlasticityModulation",
]
