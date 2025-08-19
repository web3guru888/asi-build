"""
Neuromorphic Vision Processing

Implements event-based vision systems including:
- Dynamic Vision Sensor (DVS) processing
- Spike-based feature extraction
- Temporal contrast detection
- Event-based tracking
- Neuromorphic object recognition
"""

from .dvs_processor import DVSProcessor, DVSConfig, DVSEvent
from .spike_vision import SpikeBasedVision, EventStream
from .temporal_contrast import TemporalContrast, ContrastDetector
from .event_tracker import EventBasedTracking, MotionTracker
from .feature_extractor import SpikeFeatureExtractor, OrientationDetector
from .object_recognition import NeuromorphicObjectRecognition

__all__ = [
    'DVSProcessor',
    'DVSConfig',
    'DVSEvent',
    'SpikeBasedVision',
    'EventStream',
    'TemporalContrast',
    'ContrastDetector',
    'EventBasedTracking',
    'MotionTracker',
    'SpikeFeatureExtractor',
    'OrientationDetector',
    'NeuromorphicObjectRecognition'
]