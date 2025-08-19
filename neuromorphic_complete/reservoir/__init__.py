"""
Reservoir Computing Module

Implements reservoir computing systems including:
- Liquid State Machines (LSMs)
- Echo State Networks (ESNs)
- Dynamic reservoirs
- Readout learning
- Temporal pattern processing
"""

from .liquid_state_machine import LiquidStateMachine, LSMConfig
from .echo_state_network import EchoStateNetwork, ESNConfig
from .reservoir_computer import ReservoirComputer, ReservoirConfig
from .dynamic_reservoir import DynamicReservoir, AdaptiveReservoir
from .readout_learning import ReadoutLearning, LinearReadout, NonlinearReadout

__all__ = [
    'LiquidStateMachine',
    'LSMConfig',
    'EchoStateNetwork', 
    'ESNConfig',
    'ReservoirComputer',
    'ReservoirConfig',
    'DynamicReservoir',
    'AdaptiveReservoir',
    'ReadoutLearning',
    'LinearReadout',
    'NonlinearReadout'
]