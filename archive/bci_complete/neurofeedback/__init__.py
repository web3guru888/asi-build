"""
Neurofeedback Training Module

Real-time neurofeedback systems for brain training and rehabilitation.
Includes alpha, beta, theta training and SMR protocols.
"""

from .trainer import NeurofeedbackTrainer
from .protocols import NeurofeedbackProtocols
from .feedback_controller import FeedbackController
from .session_manager import SessionManager

__all__ = [
    'NeurofeedbackTrainer',
    'NeurofeedbackProtocols',
    'FeedbackController',
    'SessionManager'
]