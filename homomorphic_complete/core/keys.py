"""
Key generation and management for homomorphic encryption schemes.
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import pickle
import hashlib
import logging

from .base import FHEException
from .parameters import FHEParameters
from .polynomial import PolynomialRing, Polynomial
from .modular import ModularArithmetic

logger = logging.getLogger(__name__)


@dataclass
class KeyMetadata:
    """Metadata for encryption keys."""
    key_id: str
    creation_time: float
    parameters_hash: str
    key_type: str
    security_level: str


class SecretKey:
    """Secret key for homomorphic encryption."""
    
    def __init__(self, polynomial: Polynomial, metadata: KeyMetadata):
        """
        Initialize a secret key.
        
        Args:
            polynomial: The secret key polynomial
            metadata: Key metadata
        """
        self.polynomial = polynomial
        self.metadata = metadata
        self._validate()
    
    def _validate(self):
        """Validate the secret key."""
        if not isinstance(self.polynomial, Polynomial):
            raise FHEException("Secret key must be a polynomial")
        
        # Check that secret key has small coefficients (typically {-1, 0, 1})
        coeffs = self.polynomial.coefficients
        if not all(abs(c) <= 1 for c in coeffs):
            logger.warning("Secret key coefficients are not small")
    
    def __str__(self) -> str:
        return f"SecretKey(id={self.metadata.key_id[:8]}...)"
    
    def serialize(self) -> bytes:
        """Serialize the secret key."""
        return pickle.dumps({
            'polynomial': self.polynomial,
            'metadata': self.metadata
        })
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'SecretKey':
        """Deserialize a secret key."""
        obj = pickle.loads(data)
        return cls(obj['polynomial'], obj['metadata'])


class PublicKey:
    """Public key for homomorphic encryption."""
    
    def __init__(self, polynomials: List[Polynomial], metadata: KeyMetadata):
        """
        Initialize a public key.
        
        Args:
            polynomials: List of polynomials forming the public key
            metadata: Key metadata
        """
        self.polynomials = polynomials
        self.metadata = metadata
        self._validate()
    
    def _validate(self):
        """Validate the public key."""
        if not self.polynomials:
            raise FHEException("Public key cannot be empty")
        
        if not all(isinstance(p, Polynomial) for p in self.polynomials):
            raise FHEException("Public key must contain polynomials")
    
    def __str__(self) -> str:
        return f"PublicKey(id={self.metadata.key_id[:8]}..., size={len(self.polynomials)})"
    
    def serialize(self) -> bytes:
        """Serialize the public key."""
        return pickle.dumps({
            'polynomials': self.polynomials,
            'metadata': self.metadata
        })
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'PublicKey':
        """Deserialize a public key."""
        obj = pickle.loads(data)
        return cls(obj['polynomials'], obj['metadata'])


class RelinearizationKeys:
    """Relinearization keys for reducing ciphertext size after multiplication."""
    
    def __init__(self, key_matrices: List[List[Polynomial]], metadata: KeyMetadata):
        """
        Initialize relinearization keys.
        
        Args:
            key_matrices: Matrices of polynomials for relinearization
            metadata: Key metadata
        """
        self.key_matrices = key_matrices
        self.metadata = metadata
    
    def __str__(self) -> str:
        return f"RelinKeys(id={self.metadata.key_id[:8]}..., levels={len(self.key_matrices)})"
    
    def serialize(self) -> bytes:
        """Serialize the relinearization keys."""
        return pickle.dumps({
            'key_matrices': self.key_matrices,
            'metadata': self.metadata
        })
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'RelinearizationKeys':
        """Deserialize relinearization keys."""
        obj = pickle.loads(data)
        return cls(obj['key_matrices'], obj['metadata'])


class GaloisKeys:
    """Galois keys for rotation operations."""
    
    def __init__(self, key_map: Dict[int, List[Polynomial]], metadata: KeyMetadata):
        """
        Initialize Galois keys.
        
        Args:
            key_map: Mapping from Galois elements to key polynomials
            metadata: Key metadata
        """
        self.key_map = key_map
        self.metadata = metadata
    
    def __str__(self) -> str:
        return f"GaloisKeys(id={self.metadata.key_id[:8]}..., elements={len(self.key_map)})"
    
    def serialize(self) -> bytes:
        """Serialize the Galois keys."""
        return pickle.dumps({
            'key_map': self.key_map,
            'metadata': self.metadata
        })
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'GaloisKeys':
        """Deserialize Galois keys."""
        obj = pickle.loads(data)
        return cls(obj['key_map'], obj['metadata'])


class KeyGenerator:
    """Generator for homomorphic encryption keys."""
    
    def __init__(self, parameters: FHEParameters):
        """
        Initialize the key generator.
        
        Args:
            parameters: FHE parameters
        """
        self.parameters = parameters
        self.poly_ring = PolynomialRing(
            parameters.polynomial_modulus_degree,
            parameters.coefficient_modulus
        )
        self.modular = ModularArithmetic(parameters.coefficient_modulus)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Generate parameter hash for key validation
        self.param_hash = self._hash_parameters()
    
    def _hash_parameters(self) -> str:
        """Generate a hash of the parameters for key validation."""
        param_str = (
            f"{self.parameters.polynomial_modulus_degree}"
            f"{self.parameters.coefficient_modulus}"
            f"{self.parameters.plaintext_modulus}"
            f"{self.parameters.scale}"
            f"{self.parameters.security_level.value}"
            f"{self.parameters.scheme_type.value}"
        )
        return hashlib.sha256(param_str.encode()).hexdigest()
    
    def generate_secret_key(self) -> SecretKey:
        """
        Generate a secret key.
        
        Returns:
            Generated secret key
        """
        # Generate secret key with small coefficients {-1, 0, 1}
        # Hamming weight is typically N/3 for security
        n = self.parameters.polynomial_modulus_degree
        hamming_weight = n // 3
        
        # Create coefficient vector
        coefficients = [0] * n
        
        # Set random positions to ±1
        positions = random.sample(range(n), hamming_weight * 2)
        for i, pos in enumerate(positions):
            coefficients[pos] = 1 if i < hamming_weight else -1
        
        # Create secret key polynomial
        secret_poly = Polynomial(coefficients, self.poly_ring)
        
        # Create metadata
        key_id = self._generate_key_id()
        metadata = KeyMetadata(
            key_id=key_id,
            creation_time=__import__('time').time(),
            parameters_hash=self.param_hash,
            key_type="secret",
            security_level=self.parameters.security_level.value
        )
        
        secret_key = SecretKey(secret_poly, metadata)
        self.logger.info(f"Generated secret key {key_id[:8]}...")
        
        return secret_key
    
    def generate_public_key(self, secret_key: SecretKey) -> PublicKey:
        """
        Generate a public key from a secret key.
        
        Args:
            secret_key: The secret key
        
        Returns:
            Generated public key
        """
        # Validate secret key
        if secret_key.metadata.parameters_hash != self.param_hash:
            raise FHEException("Secret key parameters don't match current parameters")
        
        n = self.parameters.polynomial_modulus_degree
        
        # Generate random polynomial a
        a_coeffs = [random.randint(0, q - 1) for q in self.parameters.coefficient_modulus]
        a_poly = self.poly_ring.random_polynomial()
        
        # Generate error polynomial e with Gaussian noise
        error_coeffs = self._sample_gaussian_noise(n)
        error_poly = Polynomial(error_coeffs, self.poly_ring)
        
        # Compute b = -(a*s + e) mod q
        as_product = self.poly_ring.multiply(a_poly, secret_key.polynomial)
        b_poly = self.poly_ring.add(as_product, error_poly)
        b_poly = self.poly_ring.negate(b_poly)
        
        # Public key is (b, a)
        public_polynomials = [b_poly, a_poly]
        
        # Create metadata
        key_id = self._generate_key_id()
        metadata = KeyMetadata(
            key_id=key_id,
            creation_time=__import__('time').time(),
            parameters_hash=self.param_hash,
            key_type="public",
            security_level=self.parameters.security_level.value
        )
        
        public_key = PublicKey(public_polynomials, metadata)
        self.logger.info(f"Generated public key {key_id[:8]}...")
        
        return public_key
    
    def generate_relinearization_keys(self, secret_key: SecretKey, max_level: int = 2) -> RelinearizationKeys:
        """
        Generate relinearization keys for reducing ciphertext size.
        
        Args:
            secret_key: The secret key
            max_level: Maximum ciphertext level to support
        
        Returns:
            Generated relinearization keys
        """
        key_matrices = []
        
        for level in range(2, max_level + 1):
            # Generate keys for relinearizing from level to level-1
            level_keys = []
            
            # Compute s^level
            s_power = secret_key.polynomial
            for _ in range(level - 1):
                s_power = self.poly_ring.multiply(s_power, secret_key.polynomial)
            
            # Generate key-switching keys
            for i, q in enumerate(self.parameters.coefficient_modulus):
                # Generate random polynomials
                a = self.poly_ring.random_polynomial()
                e = Polynomial(self._sample_gaussian_noise(self.parameters.polynomial_modulus_degree), 
                             self.poly_ring)
                
                # Compute b = -(a*s + e) + s^level * base^i
                base = 2 ** 60  # Decomposition base
                as_product = self.poly_ring.multiply(a, secret_key.polynomial)
                b = self.poly_ring.add(as_product, e)
                b = self.poly_ring.negate(b)
                
                # Add s^level * base^i
                s_power_scaled = self.poly_ring.scalar_multiply(s_power, base ** i)
                b = self.poly_ring.add(b, s_power_scaled)
                
                level_keys.append([b, a])
            
            key_matrices.append(level_keys)
        
        # Create metadata
        key_id = self._generate_key_id()
        metadata = KeyMetadata(
            key_id=key_id,
            creation_time=__import__('time').time(),
            parameters_hash=self.param_hash,
            key_type="relinearization",
            security_level=self.parameters.security_level.value
        )
        
        relin_keys = RelinearizationKeys(key_matrices, metadata)
        self.logger.info(f"Generated relinearization keys {key_id[:8]}... for {max_level} levels")
        
        return relin_keys
    
    def generate_galois_keys(self, secret_key: SecretKey, steps: List[int]) -> GaloisKeys:
        """
        Generate Galois keys for rotation operations.
        
        Args:
            secret_key: The secret key
            steps: List of rotation steps to support
        
        Returns:
            Generated Galois keys
        """
        n = self.parameters.polynomial_modulus_degree
        key_map = {}
        
        for step in steps:
            # Compute Galois element for rotation by step
            galois_element = self._compute_galois_element(step, n)
            
            # Apply Galois automorphism to secret key
            s_rotated = self._apply_galois_automorphism(secret_key.polynomial, galois_element)
            
            # Generate key-switching keys
            galois_key_pair = []
            
            # Generate random polynomial a
            a = self.poly_ring.random_polynomial()
            e = Polynomial(self._sample_gaussian_noise(n), self.poly_ring)
            
            # Compute b = -(a*s + e) + s_rotated
            as_product = self.poly_ring.multiply(a, secret_key.polynomial)
            b = self.poly_ring.add(as_product, e)
            b = self.poly_ring.negate(b)
            b = self.poly_ring.add(b, s_rotated)
            
            galois_key_pair = [b, a]
            key_map[galois_element] = galois_key_pair
        
        # Create metadata
        key_id = self._generate_key_id()
        metadata = KeyMetadata(
            key_id=key_id,
            creation_time=__import__('time').time(),
            parameters_hash=self.param_hash,
            key_type="galois",
            security_level=self.parameters.security_level.value
        )
        
        galois_keys = GaloisKeys(key_map, metadata)
        self.logger.info(f"Generated Galois keys {key_id[:8]}... for {len(steps)} steps")
        
        return galois_keys
    
    def _sample_gaussian_noise(self, size: int) -> List[int]:
        """
        Sample Gaussian noise for error polynomials.
        
        Args:
            size: Number of coefficients to sample
        
        Returns:
            List of noise coefficients
        """
        std_dev = self.parameters.noise_standard_deviation
        noise = np.random.normal(0, std_dev, size)
        return [int(round(x)) for x in noise]
    
    def _generate_key_id(self) -> str:
        """Generate a unique key identifier."""
        import uuid
        return str(uuid.uuid4())
    
    def _compute_galois_element(self, step: int, n: int) -> int:
        """
        Compute the Galois element for a rotation by the given step.
        
        Args:
            step: Rotation step
            n: Polynomial modulus degree
        
        Returns:
            Galois element
        """
        # For rotation by k steps: X^i -> X^(i+k) mod (X^n + 1)
        # This corresponds to the Galois element 5^k mod (2n)
        m = 2 * n
        
        # Find primitive root modulo m (typically 5)
        primitive_root = 5
        
        # Compute 5^step mod m
        galois_element = pow(primitive_root, step, m)
        
        return galois_element
    
    def _apply_galois_automorphism(self, polynomial: Polynomial, galois_element: int) -> Polynomial:
        """
        Apply Galois automorphism to a polynomial.
        
        Args:
            polynomial: Input polynomial
            galois_element: Galois element defining the automorphism
        
        Returns:
            Transformed polynomial
        """
        n = self.parameters.polynomial_modulus_degree
        m = 2 * n
        
        # Apply automorphism: X^i -> X^(galois_element * i mod m)
        new_coeffs = [0] * n
        
        for i, coeff in enumerate(polynomial.coefficients):
            if coeff != 0:
                new_power = (galois_element * i) % m
                
                if new_power < n:
                    new_coeffs[new_power] += coeff
                else:
                    # X^(n+k) = -X^k in cyclotomic ring
                    new_coeffs[new_power - n] -= coeff
        
        return Polynomial(new_coeffs, self.poly_ring)
    
    def export_keys(self, keys: Dict[str, Any], filepath: str, password: Optional[str] = None) -> None:
        """
        Export keys to a file with optional encryption.
        
        Args:
            keys: Dictionary of keys to export
            filepath: Output file path
            password: Optional password for encryption
        """
        data = {}
        for name, key in keys.items():
            data[name] = key.serialize()
        
        if password:
            # Encrypt the data with password
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            import base64
            import os
            
            # Generate salt
            salt = os.urandom(16)
            
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            
            # Encrypt data
            f = Fernet(key)
            encrypted_data = f.encrypt(pickle.dumps(data))
            
            # Save with salt
            with open(filepath, 'wb') as file:
                file.write(salt + encrypted_data)
        else:
            # Save unencrypted
            with open(filepath, 'wb') as file:
                pickle.dump(data, file)
        
        self.logger.info(f"Exported {len(keys)} keys to {filepath}")
    
    def import_keys(self, filepath: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Import keys from a file with optional decryption.
        
        Args:
            filepath: Input file path
            password: Optional password for decryption
        
        Returns:
            Dictionary of imported keys
        """
        if password:
            # Decrypt the data
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            import base64
            
            with open(filepath, 'rb') as file:
                salt = file.read(16)
                encrypted_data = file.read()
            
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            
            # Decrypt data
            f = Fernet(key)
            decrypted_data = f.decrypt(encrypted_data)
            data = pickle.loads(decrypted_data)
        else:
            # Load unencrypted
            with open(filepath, 'rb') as file:
                data = pickle.load(file)
        
        # Deserialize keys
        keys = {}
        for name, serialized_key in data.items():
            # Determine key type and deserialize
            if 'secret' in name.lower():
                keys[name] = SecretKey.deserialize(serialized_key)
            elif 'public' in name.lower():
                keys[name] = PublicKey.deserialize(serialized_key)
            elif 'relin' in name.lower():
                keys[name] = RelinearizationKeys.deserialize(serialized_key)
            elif 'galois' in name.lower():
                keys[name] = GaloisKeys.deserialize(serialized_key)
        
        self.logger.info(f"Imported {len(keys)} keys from {filepath}")
        return keys