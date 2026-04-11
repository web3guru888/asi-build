"""
Neuromorphic Hardware Simulation Module

Simulates various neuromorphic computing architectures including:
- Intel Loihi chips
- IBM TrueNorth
- SpiNNaker systems
- Memristive crossbar arrays
- Custom neuromorphic processors
"""

try:
    from .chip_simulator import ChipConfig, NeuromorphicChip
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuromorphicChip = None
    ChipConfig = None
try:
    from .memristive_device import MemristiveDevice, MemristorArray
except (ImportError, ModuleNotFoundError, SyntaxError):
    MemristiveDevice = None
    MemristorArray = None
try:
    from .synaptic_array import CrossbarArray, SynapticArray
except (ImportError, ModuleNotFoundError, SyntaxError):
    SynapticArray = None
    CrossbarArray = None
try:
    from .hardware_simulator import HardwareSimulator
except (ImportError, ModuleNotFoundError, SyntaxError):
    HardwareSimulator = None
try:
    from .loihi_simulator import LoihiChip
except (ImportError, ModuleNotFoundError, SyntaxError):
    LoihiChip = None
try:
    from .truenorth_simulator import TrueNorthChip
except (ImportError, ModuleNotFoundError, SyntaxError):
    TrueNorthChip = None
try:
    from .spinnaker_simulator import SpiNNakerChip
except (ImportError, ModuleNotFoundError, SyntaxError):
    SpiNNakerChip = None

__all__ = [
    "NeuromorphicChip",
    "ChipConfig",
    "MemristiveDevice",
    "MemristorArray",
    "SynapticArray",
    "CrossbarArray",
    "HardwareSimulator",
    "LoihiChip",
    "TrueNorthChip",
    "SpiNNakerChip",
]
