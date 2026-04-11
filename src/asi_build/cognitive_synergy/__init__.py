"""
Cognitive Synergy Module — ASI:BUILD

Information-theoretic synergy metrics, self-organization mechanisms,
pattern reasoning, and cognitive engine integration.

Key classes:
- SynergyMetrics: Mutual information, transfer entropy, phase locking, LZ complexity
- CognitiveSynergyEngine: Core engine coordinating cognitive module interactions
- EmergentPropertyDetector: Detects emergent behaviors in multi-module systems
- PRIMUSFoundation: Cognitive primitive operations (PRIMUS framework)
- PatternMiningEngine: Pattern discovery and hierarchy building
- ReasoningEngine: Deductive, inductive, abductive reasoning
"""

from asi_build.cognitive_synergy.core.synergy_metrics import (
    SynergyMetrics,
    SynergyMeasurement,
    SynergyProfile,
)
from asi_build.cognitive_synergy.core.cognitive_synergy_engine import (
    CognitiveSynergyEngine,
    SynergyPair,
    CognitiveDynamic,
)
from asi_build.cognitive_synergy.core.emergent_properties import (
    EmergentPropertyDetector,
    EmergentProperty,
    EmergenceSignature,
)
from asi_build.cognitive_synergy.core.primus_foundation import (
    PRIMUSFoundation,
    PRIMUSState,
    CognitivePrimitive,
)
from asi_build.cognitive_synergy.core.self_organization import (
    SelfOrganizationMechanism,
    HomeostaticController,
    AdaptiveRestructurer,
)
from asi_build.cognitive_synergy.pattern_reasoning.reasoning_engine import (
    ReasoningEngine,
    ReasoningType,
)
from asi_build.cognitive_synergy.pattern_reasoning.pattern_mining_engine import (
    PatternMiningEngine,
    Pattern,
)

__all__ = [
    # Core metrics
    "SynergyMetrics",
    "SynergyMeasurement",
    "SynergyProfile",
    # Engine
    "CognitiveSynergyEngine",
    "SynergyPair",
    "CognitiveDynamic",
    # Emergence
    "EmergentPropertyDetector",
    "EmergentProperty",
    "EmergenceSignature",
    # PRIMUS
    "PRIMUSFoundation",
    "PRIMUSState",
    "CognitivePrimitive",
    # Self-organization
    "SelfOrganizationMechanism",
    "HomeostaticController",
    "AdaptiveRestructurer",
    # Reasoning
    "ReasoningEngine",
    "ReasoningType",
    # Pattern mining
    "PatternMiningEngine",
    "Pattern",
]

__version__ = "2.0.0"
