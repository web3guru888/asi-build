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

try:
    from .stdp import (
        STDPLearning,
        PairSTDP,
        TripletSTDP,
        VoltageSTDP
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    STDPLearning = None
    PairSTDP = None
    TripletSTDP = None
    VoltageSTDP = None

try:
    from .homeostatic_plasticity import (
        HomeostasticPlasticity,
        SynapticScaling,
        IntrinsicPlasticity,
        ActivityDependentScaling
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    HomeostasticPlasticity = None
    SynapticScaling = None
    IntrinsicPlasticity = None
    ActivityDependentScaling = None

try:
    from .metaplasticity import (
        MetaplasticityLearning,
        BCMRule,
        SlidingThreshold,
        PriorExperienceRule
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    MetaplasticityLearning = None
    BCMRule = None
    SlidingThreshold = None
    PriorExperienceRule = None

try:
    from .temporal_learning import (
        TemporalLearning,
        SequenceLearning,
        PatternCompletion,
        TemporalMemory
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    TemporalLearning = None
    SequenceLearning = None
    PatternCompletion = None
    TemporalMemory = None

try:
    from .reinforcement import (
        ReinforcementLearning,
        DopamineModulation,
        RewardPredictionError,
        ActorCriticLearning
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    ReinforcementLearning = None
    DopamineModulation = None
    RewardPredictionError = None
    ActorCriticLearning = None

try:
    from .unsupervised import (
        UnsupervisedLearning,
        CompetitiveLearning,
        SparseCodeLearning,
        PrincipalComponentLearning
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    UnsupervisedLearning = None
    CompetitiveLearning = None
    SparseCodeLearning = None
    PrincipalComponentLearning = None

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