"""
Neuromorphic Hardware Simulation Module

Simulates various neuromorphic computing architectures including:
- Intel Loihi chips
- IBM TrueNorth
- SpiNNaker systems
- Memristive crossbar arrays
- Custom neuromorphic processors
"""

from .chip_simulator import NeuromorphicChip, ChipConfig
from .memristive_device import MemristiveDevice, MemristorArray
from .synaptic_array import SynapticArray, CrossbarArray
from .hardware_simulator import HardwareSimulator
from .loihi_simulator import LoihiChip
from .truenorth_simulator import TrueNorthChip
from .spinnaker_simulator import SpiNNakerChip

__all__ = [
    'NeuromorphicChip',
    'ChipConfig',
    'MemristiveDevice', 
    'MemristorArray',
    'SynapticArray',
    'CrossbarArray',
    'HardwareSimulator',
    'LoihiChip',
    'TrueNorthChip', 
    'SpiNNakerChip'
]