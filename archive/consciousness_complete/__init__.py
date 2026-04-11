"""
AGI Consciousness Testing Framework for Ben Goertzel's Research
=============================================================

A comprehensive framework for measuring, analyzing, and tracking machine consciousness
across multiple theoretical foundations including IIT, GWT, Attention Schema Theory,
Higher-Order Thought Theory, and more.

Author: Kenny AGI Research Division
License: MIT
"""

from .consciousness_orchestrator import ConsciousnessOrchestrator
from .theories.integrated_information import IITCalculator
from .theories.global_workspace import GWTImplementation
from .theories.attention_schema import AttentionSchemaAnalyzer
from .theories.higher_order_thought import HOTTheoryImplementation
from .theories.predictive_processing import PredictiveProcessingMetrics
from .analyzers.qualia_mapper import QualiaSpaceMapper
from .analyzers.self_model import SelfModelAnalyzer
from .analyzers.metacognition import MetacognitionAssessor
from .analyzers.agency_detector import AgencyDetector
from .trackers.consciousness_evolution import ConsciousnessEvolutionTracker
from .benchmarks.biological_markers import BiologicalConsciousnessMarkers

__version__ = "1.0.0"
__author__ = "Kenny AGI Research Division"

# Framework components
__all__ = [
    'ConsciousnessOrchestrator',
    'IITCalculator',
    'GWTImplementation',
    'AttentionSchemaAnalyzer',
    'HOTTheoryImplementation',
    'PredictiveProcessingMetrics',
    'QualiaSpaceMapper',
    'SelfModelAnalyzer',
    'MetacognitionAssessor',
    'AgencyDetector',
    'ConsciousnessEvolutionTracker',
    'BiologicalConsciousnessMarkers'
]