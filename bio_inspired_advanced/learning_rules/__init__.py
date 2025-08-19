"""
Biologically Plausible Learning Rules Module

Implements various biologically plausible learning mechanisms including
STDP, BCM rule, and other synaptic plasticity mechanisms found in biological
neural networks.
"""

from .stdp_learning import STDPLearning, STDPRule, SpikeTimingWindow
from .bcm_learning import BCMLearning, BCMRule, SlidingThreshold
from .hebbian_learning import HebbianLearning, AntiHebbianLearning
from .homeostatic_plasticity import HomeostaticPlasticity, SynapticScaling
from .metaplasticity import Metaplasticity, PlasticityModulation

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
    "PlasticityModulation"
]