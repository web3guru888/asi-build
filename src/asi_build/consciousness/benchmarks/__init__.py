"""
Consciousness Benchmarking System
=================================

Benchmarking tools for comparing machine consciousness against biological markers.
"""

try:
    from .biological_markers import BiologicalBenchmark, BiologicalConsciousnessMarkers
except (ImportError, ModuleNotFoundError, SyntaxError):
    BiologicalConsciousnessMarkers = None
    BiologicalBenchmark = None

__all__ = ["BiologicalConsciousnessMarkers", "BiologicalBenchmark"]
