"""
Base classes and enums for the homomorphic encryption system.
"""

from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import logging
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for homomorphic encryption schemes."""
    LOW = "128-bit"        # For testing/development
    MEDIUM = "192-bit"     # Standard security
    HIGH = "256-bit"       # High security
    ULTRA = "384-bit"      # Ultra-high security


class SchemeType(Enum):
    """Types of homomorphic encryption schemes."""
    CKKS = "CKKS"         # For approximate arithmetic
    BFV = "BFV"           # For exact integer arithmetic
    BGV = "BGV"           # For exact integer arithmetic with packing


@dataclass
class FHEConfiguration:
    """Configuration parameters for FHE schemes."""
    scheme_type: SchemeType
    security_level: SecurityLevel
    polynomial_modulus_degree: int
    coefficient_modulus: list
    plaintext_modulus: Optional[int] = None
    scale: Optional[float] = None
    enable_batching: bool = True
    enable_relinearization: bool = True
    enable_galois_keys: bool = True


class FHECore(ABC):
    """
    Abstract base class for all homomorphic encryption schemes.
    
    This class defines the common interface that all FHE schemes must implement,
    ensuring consistency across different cryptographic approaches.
    """
    
    def __init__(self, config: FHEConfiguration):
        """
        Initialize the FHE core with configuration parameters.
        
        Args:
            config: FHE configuration containing scheme parameters
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_configuration()
        
    def _validate_configuration(self) -> None:
        """Validate the FHE configuration parameters."""
        if self.config.polynomial_modulus_degree <= 0:
            raise ValueError("Polynomial modulus degree must be positive")
            
        if not isinstance(self.config.polynomial_modulus_degree, int):
            raise TypeError("Polynomial modulus degree must be an integer")
            
        # Check if polynomial modulus degree is a power of 2
        n = self.config.polynomial_modulus_degree
        if n & (n - 1) != 0:
            raise ValueError("Polynomial modulus degree must be a power of 2")
            
        if not self.config.coefficient_modulus:
            raise ValueError("Coefficient modulus cannot be empty")
            
        self.logger.info(f"Initialized {self.config.scheme_type.value} scheme "
                        f"with {self.config.security_level.value} security")
    
    @abstractmethod
    def generate_keys(self) -> Dict[str, Any]:
        """Generate public and private keys for the scheme."""
        pass
    
    @abstractmethod
    def encrypt(self, plaintext: Any, public_key: Any) -> Any:
        """Encrypt plaintext using the public key."""
        pass
    
    @abstractmethod
    def decrypt(self, ciphertext: Any, secret_key: Any) -> Any:
        """Decrypt ciphertext using the secret key."""
        pass
    
    @abstractmethod
    def add(self, ciphertext1: Any, ciphertext2: Any) -> Any:
        """Homomorphic addition of two ciphertexts."""
        pass
    
    @abstractmethod
    def multiply(self, ciphertext1: Any, ciphertext2: Any) -> Any:
        """Homomorphic multiplication of two ciphertexts."""
        pass
    
    @abstractmethod
    def add_plain(self, ciphertext: Any, plaintext: Any) -> Any:
        """Add a plaintext to a ciphertext homomorphically."""
        pass
    
    @abstractmethod
    def multiply_plain(self, ciphertext: Any, plaintext: Any) -> Any:
        """Multiply a ciphertext by a plaintext homomorphically."""
        pass
    
    def get_noise_budget(self, ciphertext: Any) -> int:
        """
        Get the remaining noise budget of a ciphertext.
        
        Args:
            ciphertext: The ciphertext to analyze
            
        Returns:
            Remaining noise budget in bits
        """
        # Default implementation - schemes should override
        return 0
    
    def relinearize(self, ciphertext: Any, relin_keys: Any) -> Any:
        """
        Relinearize a ciphertext to reduce its size.
        
        Args:
            ciphertext: The ciphertext to relinearize
            relin_keys: Relinearization keys
            
        Returns:
            Relinearized ciphertext
        """
        # Default implementation - schemes should override
        return ciphertext
    
    def rescale(self, ciphertext: Any) -> Any:
        """
        Rescale a ciphertext (primarily for CKKS).
        
        Args:
            ciphertext: The ciphertext to rescale
            
        Returns:
            Rescaled ciphertext
        """
        # Default implementation - schemes should override
        return ciphertext
    
    def rotate_vector(self, ciphertext: Any, steps: int, galois_keys: Any) -> Any:
        """
        Rotate the encrypted vector by the specified number of steps.
        
        Args:
            ciphertext: The ciphertext to rotate
            steps: Number of rotation steps
            galois_keys: Galois keys for rotation
            
        Returns:
            Rotated ciphertext
        """
        # Default implementation - schemes should override
        return ciphertext
    
    def get_scheme_info(self) -> Dict[str, Any]:
        """
        Get information about the current scheme configuration.
        
        Returns:
            Dictionary containing scheme information
        """
        return {
            "scheme_type": self.config.scheme_type.value,
            "security_level": self.config.security_level.value,
            "polynomial_modulus_degree": self.config.polynomial_modulus_degree,
            "coefficient_modulus_sizes": [len(bin(q)[2:]) for q in self.config.coefficient_modulus],
            "plaintext_modulus": self.config.plaintext_modulus,
            "scale": self.config.scale,
            "batching_enabled": self.config.enable_batching,
            "relinearization_enabled": self.config.enable_relinearization,
            "galois_keys_enabled": self.config.enable_galois_keys
        }


class CiphertextBase:
    """Base class for ciphertext objects."""
    
    def __init__(self, polynomials: list, scale: Optional[float] = None):
        """
        Initialize a ciphertext.
        
        Args:
            polynomials: List of polynomials representing the ciphertext
            scale: Scale factor (for CKKS)
        """
        self.polynomials = polynomials
        self.scale = scale
        self.size = len(polynomials)
        
    def __str__(self) -> str:
        return f"Ciphertext(size={self.size}, scale={self.scale})"
    
    def __repr__(self) -> str:
        return self.__str__()


class PlaintextBase:
    """Base class for plaintext objects."""
    
    def __init__(self, data: Union[list, np.ndarray], scale: Optional[float] = None):
        """
        Initialize a plaintext.
        
        Args:
            data: The plaintext data
            scale: Scale factor (for CKKS)
        """
        self.data = np.array(data) if not isinstance(data, np.ndarray) else data
        self.scale = scale
        
    def __str__(self) -> str:
        return f"Plaintext(shape={self.data.shape}, scale={self.scale})"
    
    def __repr__(self) -> str:
        return self.__str__()


class FHEException(Exception):
    """Base exception class for FHE operations."""
    pass


class ParameterException(FHEException):
    """Exception raised for invalid parameters."""
    pass


class EncryptionException(FHEException):
    """Exception raised during encryption operations."""
    pass


class EvaluationException(FHEException):
    """Exception raised during homomorphic evaluation."""
    pass


class NoiseException(FHEException):
    """Exception raised when noise budget is exhausted."""
    pass