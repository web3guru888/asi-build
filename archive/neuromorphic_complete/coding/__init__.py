"""
Neural Coding Schemes

Implements various neural coding strategies including:
- Rate coding
- Temporal coding  
- Population coding
- Sparse coding
- Rank order coding
- Phase coding
"""

from .rate_codec import RateCodec, RateEncoder, RateDecoder
from .temporal_codec import TemporalCodec, TimingEncoder, TimingDecoder
from .population_codec import PopulationCodec, PopulationEncoder, PopulationDecoder
from .sparse_codec import SparseCodec, SparseEncoder, SparseDecoder
from .rank_order_codec import RankOrderCodec, RankEncoder, RankDecoder
from .phase_codec import PhaseCodec, PhaseEncoder, PhaseDecoder

__all__ = [
    'RateCodec',
    'RateEncoder',
    'RateDecoder',
    'TemporalCodec',
    'TimingEncoder', 
    'TimingDecoder',
    'PopulationCodec',
    'PopulationEncoder',
    'PopulationDecoder',
    'SparseCodec',
    'SparseEncoder',
    'SparseDecoder',
    'RankOrderCodec',
    'RankEncoder',
    'RankDecoder',
    'PhaseCodec',
    'PhaseEncoder',
    'PhaseDecoder'
]