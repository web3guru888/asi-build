"""
Encrypted machine learning modules using homomorphic encryption.
"""

try:
    from .neural_networks import EncryptedNeuralNetwork, EncryptedLayer
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedNeuralNetwork = None
    EncryptedLayer = None
try:
    from .linear_models import EncryptedLinearRegression, EncryptedLogisticRegression
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedLinearRegression = None
    EncryptedLogisticRegression = None
try:
    from .ensemble import EncryptedRandomForest, EncryptedGradientBoosting
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedRandomForest = None
    EncryptedGradientBoosting = None
try:
    from .clustering import EncryptedKMeans, EncryptedDBSCAN
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedKMeans = None
    EncryptedDBSCAN = None
try:
    from .preprocessing import EncryptedPreprocessor, EncryptedScaler
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedPreprocessor = None
    EncryptedScaler = None
try:
    from .metrics import EncryptedMetrics
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedMetrics = None
try:
    from .training import EncryptedTrainer, FederatedLearning
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedTrainer = None
    FederatedLearning = None
try:
    from .inference import EncryptedInference
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedInference = None
try:
    from .privacy import DifferentialPrivacy, SecureAggregation
except (ImportError, ModuleNotFoundError, SyntaxError):
    DifferentialPrivacy = None
    SecureAggregation = None

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