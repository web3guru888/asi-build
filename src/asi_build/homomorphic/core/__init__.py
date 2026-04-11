"""
Core homomorphic encryption components and utilities.
"""

try:
    from .base import FHECore, SecurityLevel
except (ImportError, ModuleNotFoundError, SyntaxError):
    FHECore = None
    SecurityLevel = None
try:
    from .parameters import ParameterGenerator, FHEParameters
except (ImportError, ModuleNotFoundError, SyntaxError):
    ParameterGenerator = None
    FHEParameters = None
try:
    from .keys import KeyGenerator, PublicKey, SecretKey, RelinearizationKeys
except (ImportError, ModuleNotFoundError, SyntaxError):
    KeyGenerator = None
    PublicKey = None
    SecretKey = None
    RelinearizationKeys = None
try:
    from .encryption import Encryptor, Decryptor
except (ImportError, ModuleNotFoundError, SyntaxError):
    Encryptor = None
    Decryptor = None
try:
    from .evaluation import Evaluator
except (ImportError, ModuleNotFoundError, SyntaxError):
    Evaluator = None
try:
    from .utils import HomomorphicUtils
except (ImportError, ModuleNotFoundError, SyntaxError):
    HomomorphicUtils = None
try:
    from .polynomial import PolynomialRing, Polynomial
except (ImportError, ModuleNotFoundError, SyntaxError):
    PolynomialRing = None
    Polynomial = None
try:
    from .modular import ModularArithmetic
except (ImportError, ModuleNotFoundError, SyntaxError):
    ModularArithmetic = None
try:
    from .noise import NoiseEstimator
except (ImportError, ModuleNotFoundError, SyntaxError):
    NoiseEstimator = None
try:
    from .optimization import OptimizationEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    OptimizationEngine = None

__all__ = [
    "FHECore",
    "SecurityLevel", 
    "ParameterGenerator",
    "FHEParameters",
    "KeyGenerator",
    "PublicKey",
    "SecretKey", 
    "RelinearizationKeys",
    "Encryptor",
    "Decryptor",
    "Evaluator",
    "HomomorphicUtils",
    "PolynomialRing",
    "Polynomial",
    "ModularArithmetic",
    "NoiseEstimator",
    "OptimizationEngine"
]