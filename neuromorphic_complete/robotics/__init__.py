"""
Neuromorphic Robotics Control

Implements brain-inspired robotic control systems including:
- Neuromorphic motor controllers
- Sensorimotor mapping
- Adaptive behavior generation
- Embodied learning
- Spike-based control
"""

from .neuromorphic_controller import NeuromorphicController, ControllerConfig
from .sensorimotor_mapper import SensoriMotorMapper, SensorProcessor
from .adaptive_behavior import AdaptiveBehavior, BehaviorLearning
from .embodied_learning import EmbodiedLearning, MotorLearning
from .spike_control import SpikeBasedControl, MotorEncoder

__all__ = [
    'NeuromorphicController',
    'ControllerConfig',
    'SensoriMotorMapper',
    'SensorProcessor',
    'AdaptiveBehavior',
    'BehaviorLearning',
    'EmbodiedLearning',
    'MotorLearning',
    'SpikeBasedControl',
    'MotorEncoder'
]