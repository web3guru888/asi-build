"""
AGI Creativity & Art Generation Platform

A comprehensive platform for exploring artificial creativity and artistic expression,
designed to push the boundaries of AGI capabilities in creative domains.

This platform implements:
- Novel concept synthesis with combinatorial creativity
- Cross-domain creative transfer learning
- Aesthetic evaluation based on art theory
- Human-AGI collaborative creation
- Multi-modal art generation
- Style transfer and artistic interpretation
- Creative constraint satisfaction
- Narrative generation with plot coherence
- Musical composition with harmonic theory
- Meta-creative AI for new art forms

Author: Claude Code AGI Platform
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Claude Code AGI Platform"

from .core import (
    ConceptSynthesizer,
    TransferLearner,
    AestheticEvaluator,
    CollaborationEngine
)

from .engines import (
    MultiModalGenerator,
    StyleTransferEngine,
    ConstraintSolver,
    NarrativeGenerator,
    MusicComposer,
    MetaCreativeAI
)

from .interfaces import (
    WebInterface,
    APIServer,
    CLIInterface
)

from .models import (
    GenerativeModels,
    AestheticRL,
    CreativeTransformers
)

from .evaluation import (
    CreativityBenchmarks,
    AestheticMetrics,
    CulturalEvaluator
)

__all__ = [
    "ConceptSynthesizer",
    "TransferLearner", 
    "AestheticEvaluator",
    "CollaborationEngine",
    "MultiModalGenerator",
    "StyleTransferEngine",
    "ConstraintSolver",
    "NarrativeGenerator",
    "MusicComposer",
    "MetaCreativeAI",
    "WebInterface",
    "APIServer",
    "CLIInterface",
    "GenerativeModels",
    "AestheticRL",
    "CreativeTransformers",
    "CreativityBenchmarks",
    "AestheticMetrics",
    "CulturalEvaluator"
]