"""
Consciousness Theory Implementations
=====================================

Implementations of major theories of consciousness for machine consciousness assessment.

Modules:
- tensor_iit: IIT 3.0 Φ computation on tensor activations (exhaustive MIP search,
  histogram-based MI, frequency-band Φ spectrum)
- higher_order_thought: HOT theory with real graph analysis (transitivity chains
  via networkx, introspective depth, PCA-based metacognitive richness)
- predictive_processing_tensor: Free energy minimization / predictive processing
  (hierarchical PP with precision weighting, Friston framework)

Note: tensor_iit and predictive_processing_tensor are complementary to the existing
top-level integrated_information.py and predictive_processing.py. The top-level files
are the original src versions; these are richer implementations rescued from
archive/consciousness_complete/ with additional capabilities (frequency-band analysis,
free energy assessment, etc.).
"""

try:
    from .tensor_iit import IITCalculator as TensorIITCalculator, PhiComplex, ConceptualStructure
    from .higher_order_thought import HOTTheoryImplementation, HOTStructure, ConsciousnessMetrics, MentalState
    from .predictive_processing_tensor import PredictiveProcessingMetrics as PredictiveProcessingTensor, PredictiveHierarchy, ConsciousPredictionMetrics

    __all__ = [
        'TensorIITCalculator',
        'PhiComplex',
        'ConceptualStructure',
        'HOTTheoryImplementation',
        'HOTStructure',
        'ConsciousnessMetrics',
        'MentalState',
        'PredictiveProcessingTensor',
        'PredictiveHierarchy',
        'ConsciousPredictionMetrics',
    ]
except (ImportError, OSError):
    # torch may not be available
    __all__ = []
