"""
Brain-Computer Interface Module

Implements neuromorphic BCI systems including:
- Spike decoding algorithms
- Motor intention detection
- Brain signal processing
- Neuroprosthetic control
- Real-time neural interfaces
"""

from .spike_decoder import SpikeDecoder, PopulationVectorDecoder, KalmanDecoder
from .motor_intention import MotorIntention, IntentionClassifier
from .brain_signal_processor import BrainSignalProcessor, SignalFilter
from .neuroprosthetic_control import NeuroprostheticControl, ControlInterface
from .neural_interface import NeuralInterface, RealtimeProcessor

__all__ = [
    'SpikeDecoder',
    'PopulationVectorDecoder',
    'KalmanDecoder',
    'MotorIntention',
    'IntentionClassifier', 
    'BrainSignalProcessor',
    'SignalFilter',
    'NeuroprostheticControl',
    'ControlInterface',
    'NeuralInterface',
    'RealtimeProcessor'
]