"""
Brain-to-Brain Interface Simulation

This module simulates brain-computer interfaces and brain-to-brain communication
technologies that could theoretically enable direct neural communication.
"""

from .bci_simulator import BCISimulator
from .neural_bridge import NeuralBridge
from .eeg_processor import EEGProcessor
from .brain_decoder import BrainDecoder

__all__ = [
    "BCISimulator",
    "NeuralBridge", 
    "EEGProcessor",
    "BrainDecoder"
]