"""
Energy Efficiency and Biological Comparison Module

Implements energy efficiency metrics and comparisons to biological neural networks
to ensure the bio-inspired cognitive architecture operates within biologically
plausible energy constraints.
"""

try:
    from .energy_metrics import EnergyCalculator, EnergyMetrics, MetabolicCost
except (ImportError, ModuleNotFoundError, SyntaxError):
    EnergyMetrics = None
    EnergyCalculator = None
    MetabolicCost = None

try:
    from .biological_efficiency import BiologicalEfficiencyComparator, NeuralEnergyBenchmark
except ImportError:
    BiologicalEfficiencyComparator = None
    NeuralEnergyBenchmark = None

try:
    from .power_management import EnergyOptimizer, PowerManager
except ImportError:
    PowerManager = None
    EnergyOptimizer = None

try:
    from .thermal_dynamics import CoolingSystem, ThermalModel
except ImportError:
    ThermalModel = None
    CoolingSystem = None

__all__ = [
    "EnergyMetrics",
    "EnergyCalculator",
    "MetabolicCost",
    "BiologicalEfficiencyComparator",
    "NeuralEnergyBenchmark",
    "PowerManager",
    "EnergyOptimizer",
    "ThermalModel",
    "CoolingSystem",
]
