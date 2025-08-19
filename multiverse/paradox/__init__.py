"""
Paradox Resolution Systems
=========================

Paradox detection and resolution systems for maintaining causal consistency
and preventing temporal/dimensional paradoxes in the multiverse framework.
"""

from .paradox_resolution_engine import ParadoxResolutionEngine, ParadoxType, ResolutionStrategy
from .causality_validator import CausalityValidator, CausalChain, CausalViolation
from .temporal_consistency_checker import TemporalConsistencyChecker, ConsistencyViolation
from .paradox_prevention_system import ParadoxPreventionSystem, PreventionRule
from .causal_loop_detector import CausalLoopDetector, CausalLoop
from .timeline_integrity_monitor import TimelineIntegrityMonitor, IntegrityBreach
from .bootstrap_paradox_resolver import BootstrapParadoxResolver, BootstrapEvent
from .grandfather_paradox_handler import GrandfatherParadoxHandler, ParadoxSolution

__all__ = [
    'ParadoxResolutionEngine', 'ParadoxType', 'ResolutionStrategy',
    'CausalityValidator', 'CausalChain', 'CausalViolation',
    'TemporalConsistencyChecker', 'ConsistencyViolation',
    'ParadoxPreventionSystem', 'PreventionRule',
    'CausalLoopDetector', 'CausalLoop',
    'TimelineIntegrityMonitor', 'IntegrityBreach',
    'BootstrapParadoxResolver', 'BootstrapEvent',
    'GrandfatherParadoxHandler', 'ParadoxSolution'
]