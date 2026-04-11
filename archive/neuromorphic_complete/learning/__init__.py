"""
Neuromorphic Learning Algorithms

Implements biologically-inspired learning rules for neuromorphic systems:
- Spike-Timing Dependent Plasticity (STDP)
- Homeostatic plasticity
- Metaplasticity
- Reinforcement learning
- Temporal pattern learning
- Unsupervised feature learning
"""

from .stdp import (
    STDPLearning,
    PairSTDP,
    TripletSTDP,
    VoltageSTDP
)

from .homeostatic_plasticity import (
    HomeostasticPlasticity,
    SynapticScaling,
    IntrinsicPlasticity,
    ActivityDependentScaling
)

from .metaplasticity import (
    MetaplasticityLearning,
    BCMRule,
    SlidingThreshold,
    PriorExperienceRule
)

from .temporal_learning import (
    TemporalLearning,
    SequenceLearning,
    PatternCompletion,
    TemporalMemory
)

from .reinforcement import (
    ReinforcementLearning,
    DopamineModulation,
    RewardPredictionError,
    ActorCriticLearning
)

from .unsupervised import (
    UnsupervisedLearning,
    CompetitiveLearning,
    SparseCodeLearning,
    PrincipalComponentLearning
)

__all__ = [
    'STDPLearning',
    'PairSTDP',
    'TripletSTDP', 
    'VoltageSTDP',
    'HomeostasticPlasticity',
    'SynapticScaling',
    'IntrinsicPlasticity',
    'ActivityDependentScaling',
    'MetaplasticityLearning',
    'BCMRule',
    'SlidingThreshold',
    'PriorExperienceRule',
    'TemporalLearning',
    'SequenceLearning',
    'PatternCompletion',
    'TemporalMemory',
    'ReinforcementLearning',
    'DopamineModulation',
    'RewardPredictionError',
    'ActorCriticLearning',
    'UnsupervisedLearning',
    'CompetitiveLearning',
    'SparseCodeLearning',
    'PrincipalComponentLearning'
]