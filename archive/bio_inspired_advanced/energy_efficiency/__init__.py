"""
Energy Efficiency and Biological Comparison Module

Implements energy efficiency metrics and comparisons to biological neural networks
to ensure the bio-inspired cognitive architecture operates within biologically
plausible energy constraints.
"""

from .energy_metrics import EnergyMetrics, EnergyCalculator, MetabolicCost
from .biological_efficiency import BiologicalEfficiencyComparator, NeuralEnergyBenchmark
from .power_management import PowerManager, EnergyOptimizer
from .thermal_dynamics import ThermalModel, CoolingSystem

__all__ = [
    "EnergyMetrics",
    "EnergyCalculator",
    "MetabolicCost",
    "BiologicalEfficiencyComparator",
    "NeuralEnergyBenchmark", 
    "PowerManager",
    "EnergyOptimizer",
    "ThermalModel",
    "CoolingSystem"
]