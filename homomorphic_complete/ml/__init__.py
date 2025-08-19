"""
Encrypted machine learning modules using homomorphic encryption.
"""

from .neural_networks import EncryptedNeuralNetwork, EncryptedLayer
from .linear_models import EncryptedLinearRegression, EncryptedLogisticRegression
from .ensemble import EncryptedRandomForest, EncryptedGradientBoosting
from .clustering import EncryptedKMeans, EncryptedDBSCAN
from .preprocessing import EncryptedPreprocessor, EncryptedScaler
from .metrics import EncryptedMetrics
from .training import EncryptedTrainer, FederatedLearning
from .inference import EncryptedInference
from .privacy import DifferentialPrivacy, SecureAggregation

__all__ = [
    # Neural Networks
    "EncryptedNeuralNetwork",
    "EncryptedLayer",
    
    # Linear Models
    "EncryptedLinearRegression",
    "EncryptedLogisticRegression",
    
    # Ensemble Methods
    "EncryptedRandomForest",
    "EncryptedGradientBoosting",
    
    # Clustering
    "EncryptedKMeans",
    "EncryptedDBSCAN",
    
    # Preprocessing
    "EncryptedPreprocessor",
    "EncryptedScaler",
    
    # Metrics
    "EncryptedMetrics",
    
    # Training
    "EncryptedTrainer",
    "FederatedLearning",
    
    # Inference
    "EncryptedInference",
    
    # Privacy
    "DifferentialPrivacy",
    "SecureAggregation"
]