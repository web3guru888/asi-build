"""
Neurofeedback Training Module

Real-time neurofeedback systems for brain training and rehabilitation.
Includes alpha, beta, theta training and SMR protocols.
"""

try:
    from .trainer import NeurofeedbackTrainer
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeurofeedbackTrainer = None
try:
    from .protocols import NeurofeedbackProtocols
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeurofeedbackProtocols = None
try:
    from .feedback_controller import FeedbackController
except (ImportError, ModuleNotFoundError, SyntaxError):
    FeedbackController = None
try:
    from .session_manager import SessionManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    SessionManager = None

__all__ = [
    'NeurofeedbackTrainer',
    'NeurofeedbackProtocols',
    'FeedbackController',
    'SessionManager'
]