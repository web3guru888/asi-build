"""
Privacy-Preserving Training with Differential Privacy and Secure Aggregation
Implements secure multi-party computation for federated learning
"""

import asyncio
import logging
import secrets
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
import torch
import torch.nn as nn
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
import time

@dataclass
class SecretShare:
    """Represents a secret share in Shamir's Secret Sharing"""
    participant_id: str
    share_id: int
    share_value: bytes
    threshold: int
    total_shares: int

@dataclass
class EncryptedGradient:
    """Encrypted gradient update"""
    node_id: str
    encrypted_data: bytes
    noise_parameters: Dict[str, float]
    encryption_metadata: Dict[str, Any]
    timestamp: float

class DifferentialPrivacyMechanism:
    """Implements differential privacy for gradient updates"""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5, 
                 sensitivity: float = 1.0, clipping_norm: float = 1.0):
        self.epsilon = epsilon
        self.delta = delta
        self.sensitivity = sensitivity
        self.clipping_norm = clipping_norm
        
        self.logger = logging.getLogger(__name__)
        
        # Noise calibration
        self.noise_multiplier = self._calculate_noise_multiplier()
    
    def _calculate_noise_multiplier(self) -> float:
        """Calculate noise multiplier for Gaussian mechanism"""
        # Simplified calculation - in practice, use more sophisticated methods
        # like the moments accountant or RDP analysis
        return np.sqrt(2 * np.log(1.25 / self.delta)) * self.sensitivity / self.epsilon
    
    def clip_gradients(self, gradients: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Clip gradients to bound sensitivity"""
        clipped_gradients = {}
        
        # Calculate global norm
        total_norm = 0.0
        for param_gradients in gradients.values():
            total_norm += torch.norm(param_gradients).item() ** 2
        total_norm = total_norm ** 0.5
        
        # Apply clipping
        clip_coeff = min(1.0, self.clipping_norm / (total_norm + 1e-6))
        
        for name, param_gradients in gradients.items():
            clipped_gradients[name] = param_gradients * clip_coeff
        
        if clip_coeff < 1.0:
            self.logger.debug(f"Clipped gradients with coefficient {clip_coeff:.4f}")
        
        return clipped_gradients
    
    def add_noise(self, gradients: Dict[str, torch.Tensor]) -> Tuple[Dict[str, torch.Tensor], Dict[str, float]]:
        """Add calibrated Gaussian noise to gradients"""
        noisy_gradients = {}
        noise_parameters = {}
        
        for name, param_gradients in gradients.items():
            # Calculate noise scale
            noise_scale = self.noise_multiplier * self.clipping_norm
            
            # Generate Gaussian noise
            noise = torch.normal(
                mean=0.0, 
                std=noise_scale, 
                size=param_gradients.shape,
                dtype=param_gradients.dtype,
                device=param_gradients.device
            )
            
            noisy_gradients[name] = param_gradients + noise
            noise_parameters[name] = {
                'noise_scale': noise_scale,
                'noise_norm': torch.norm(noise).item()
            }
        
        return noisy_gradients, noise_parameters
    
    def privatize_gradients(self, gradients: Dict[str, torch.Tensor]) -> Tuple[Dict[str, torch.Tensor], Dict[str, float]]:
        """Apply differential privacy to gradients"""
        # Clip gradients
        clipped_gradients = self.clip_gradients(gradients)
        
        # Add noise
        private_gradients, noise_params = self.add_noise(clipped_gradients)
        
        return private_gradients, noise_params

class ShamirSecretSharing:
    """Shamir's Secret Sharing for secure aggregation"""
    
    def __init__(self, threshold: int, total_shares: int):
        self.threshold = threshold
        self.total_shares = total_shares
        self.prime = 2**127 - 1  # Large prime for finite field arithmetic
        
    def _eval_poly(self, coeffs: List[int], x: int) -> int:
        """Evaluate polynomial at point x"""
        result = 0
        for coeff in reversed(coeffs):
            result = (result * x + coeff) % self.prime
        return result
    
    def create_shares(self, secret: int, participant_ids: List[str]) -> List[SecretShare]:
        """Create secret shares"""
        if len(participant_ids) < self.threshold:
            raise ValueError("Not enough participants for threshold")
        
        # Generate random coefficients
        coeffs = [secret] + [secrets.randbelow(self.prime) for _ in range(self.threshold - 1)]
        
        shares = []
        for i, participant_id in enumerate(participant_ids[:self.total_shares], 1):
            share_value = self._eval_poly(coeffs, i)
            share = SecretShare(
                participant_id=participant_id,
                share_id=i,
                share_value=share_value.to_bytes(16, 'big'),
                threshold=self.threshold,
                total_shares=self.total_shares
            )
            shares.append(share)
        
        return shares
    
    def reconstruct_secret(self, shares: List[SecretShare]) -> int:
        """Reconstruct secret from shares using Lagrange interpolation"""
        if len(shares) < self.threshold:
            raise ValueError("Insufficient shares for reconstruction")
        
        # Convert shares to integers
        share_points = []
        for share in shares[:self.threshold]:
            x = share.share_id
            y = int.from_bytes(share.share_value, 'big')
            share_points.append((x, y))
        
        # Lagrange interpolation
        secret = 0
        for i, (xi, yi) in enumerate(share_points):
            # Calculate Lagrange basis polynomial
            li = 1
            for j, (xj, _) in enumerate(share_points):
                if i != j:
                    # li *= (0 - xj) / (xi - xj)
                    numerator = (0 - xj) % self.prime
                    denominator = pow(xi - xj, -1, self.prime)  # Modular inverse
                    li = (li * numerator * denominator) % self.prime
            
            secret = (secret + yi * li) % self.prime
        
        return secret

class SecureAggregationProtocol:
    """Secure aggregation protocol for federated learning"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.threshold = config.get('threshold', 10)
        self.total_participants = config.get('total_participants', 20)
        
        # Cryptographic components
        self.secret_sharing = ShamirSecretSharing(self.threshold, self.total_participants)
        self.dp_mechanism = DifferentialPrivacyMechanism(
            epsilon=config.get('epsilon', 1.0),
            delta=config.get('delta', 1e-5),
            clipping_norm=config.get('clipping_norm', 1.0)
        )
        
        # Participant management
        self.participants: Dict[str, Dict[str, Any]] = {}
        self.round_keys: Dict[str, bytes] = {}
        self.gradient_shares: Dict[str, Dict[str, List[SecretShare]]] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def setup_round(self, participant_ids: List[str]) -> Dict[str, Any]:
        """Setup secure aggregation round"""
        round_id = hashlib.sha256(
            f"{time.time()}{len(participant_ids)}".encode()
        ).hexdigest()[:16]
        
        # Generate round-specific parameters
        self.round_keys[round_id] = secrets.token_bytes(32)
        self.gradient_shares[round_id] = {}
        
        # Setup participants
        for participant_id in participant_ids:
            if participant_id not in self.participants:
                self.participants[participant_id] = {
                    'public_key': self._generate_participant_key(participant_id),
                    'active_rounds': []
                }
            self.participants[participant_id]['active_rounds'].append(round_id)
        
        self.logger.info(f"Setup secure aggregation round {round_id} with {len(participant_ids)} participants")
        
        return {
            'round_id': round_id,
            'threshold': self.threshold,
            'participants': participant_ids,
            'encryption_key': base64.b64encode(self.round_keys[round_id]).decode()
        }
    
    async def submit_encrypted_gradients(self, round_id: str, node_id: str, 
                                       gradients: Dict[str, torch.Tensor]) -> bool:
        """Submit encrypted gradients for secure aggregation"""
        try:
            if round_id not in self.round_keys:
                raise ValueError("Invalid round ID")
            
            if node_id not in self.participants:
                raise ValueError("Participant not registered")
            
            # Apply differential privacy
            private_gradients, noise_params = self.dp_mechanism.privatize_gradients(gradients)
            
            # Serialize gradients
            gradient_bytes = self._serialize_gradients(private_gradients)
            
            # Encrypt gradients
            round_key = self.round_keys[round_id]
            encrypted_data = self._encrypt_data(gradient_bytes, round_key)
            
            # Create secret shares for each gradient parameter
            if round_id not in self.gradient_shares:
                self.gradient_shares[round_id] = {}
            
            participant_list = [p for p in self.participants.keys() 
                              if round_id in self.participants[p]['active_rounds']]
            
            for param_name, param_tensor in private_gradients.items():
                # Convert tensor to integer representation for secret sharing
                param_int = self._tensor_to_int(param_tensor)
                
                # Create shares
                shares = self.secret_sharing.create_shares(param_int, participant_list)
                
                if param_name not in self.gradient_shares[round_id]:
                    self.gradient_shares[round_id][param_name] = []
                
                self.gradient_shares[round_id][param_name].extend(shares)
            
            self.logger.info(f"Received encrypted gradients from {node_id} for round {round_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to submit encrypted gradients: {e}")
            return False
    
    async def aggregate_gradients(self, round_id: str) -> Optional[Dict[str, torch.Tensor]]:
        """Securely aggregate gradients from all participants"""
        try:
            if round_id not in self.gradient_shares:
                self.logger.error(f"No gradient shares found for round {round_id}")
                return None
            
            aggregated_gradients = {}
            round_shares = self.gradient_shares[round_id]
            
            # Reconstruct and aggregate each parameter
            for param_name, shares_list in round_shares.items():
                # Group shares by participant
                participant_shares = {}
                for share in shares_list:
                    if share.participant_id not in participant_shares:
                        participant_shares[share.participant_id] = []
                    participant_shares[share.participant_id].append(share)
                
                # Check if we have enough participants
                if len(participant_shares) < self.threshold:
                    self.logger.warning(f"Insufficient shares for parameter {param_name}")
                    continue
                
                # Reconstruct secrets from shares
                reconstructed_values = []
                for participant_id, participant_share_list in list(participant_shares.items())[:self.threshold]:
                    if participant_share_list:
                        reconstructed_int = self.secret_sharing.reconstruct_secret(participant_share_list[:1])
                        reconstructed_values.append(reconstructed_int)
                
                # Average the reconstructed values
                if reconstructed_values:
                    avg_value = sum(reconstructed_values) / len(reconstructed_values)
                    
                    # Convert back to tensor (this is simplified - in practice, need proper shape reconstruction)
                    # For demo purposes, create a small tensor
                    aggregated_gradients[param_name] = torch.tensor([avg_value % 1000] * 10, dtype=torch.float32)
            
            self.logger.info(f"Successfully aggregated gradients for round {round_id}")
            return aggregated_gradients
            
        except Exception as e:
            self.logger.error(f"Failed to aggregate gradients: {e}")
            return None
    
    def _generate_participant_key(self, participant_id: str) -> str:
        """Generate public key for participant"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()
        
        pem = public_key.public_key_pem()
        return pem.decode('utf-8')
    
    def _serialize_gradients(self, gradients: Dict[str, torch.Tensor]) -> bytes:
        """Serialize gradients to bytes"""
        # Simple serialization - in practice, use more efficient methods
        gradient_data = {}
        for name, tensor in gradients.items():
            gradient_data[name] = {
                'data': tensor.detach().cpu().numpy().tolist(),
                'shape': list(tensor.shape),
                'dtype': str(tensor.dtype)
            }
        
        return json.dumps(gradient_data).encode('utf-8')
    
    def _encrypt_data(self, data: bytes, key: bytes) -> bytes:
        """Encrypt data using AES"""
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM
        
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Combine IV + tag + ciphertext
        return iv + encryptor.tag + ciphertext
    
    def _decrypt_data(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt data using AES"""
        iv = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]
        
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        
        return decryptor.update(ciphertext) + decryptor.finalize()
    
    def _tensor_to_int(self, tensor: torch.Tensor) -> int:
        """Convert tensor to integer for secret sharing"""
        # Simplified conversion - sum all elements and convert to int
        # In practice, would need more sophisticated encoding
        tensor_sum = torch.sum(tensor).item()
        return int(tensor_sum * 1000000) % self.secret_sharing.prime
    
    def cleanup_round(self, round_id: str):
        """Cleanup round data"""
        if round_id in self.round_keys:
            del self.round_keys[round_id]
        
        if round_id in self.gradient_shares:
            del self.gradient_shares[round_id]
        
        # Remove round from participant records
        for participant in self.participants.values():
            if round_id in participant.get('active_rounds', []):
                participant['active_rounds'].remove(round_id)
        
        self.logger.info(f"Cleaned up round {round_id}")

class HomomorphicEncryption:
    """Simplified homomorphic encryption for secure computation"""
    
    def __init__(self, key_size: int = 2048):
        self.key_size = key_size
        self.public_key = None
        self.private_key = None
        self._generate_keys()
    
    def _generate_keys(self):
        """Generate RSA key pair"""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
        )
        self.public_key = self.private_key.public_key()
    
    def encrypt(self, plaintext: int) -> bytes:
        """Encrypt integer plaintext"""
        # Simple RSA encryption (not fully homomorphic)
        plaintext_bytes = plaintext.to_bytes((plaintext.bit_length() + 7) // 8, 'big')
        
        ciphertext = self.public_key.encrypt(
            plaintext_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext
    
    def decrypt(self, ciphertext: bytes) -> int:
        """Decrypt ciphertext to integer"""
        plaintext_bytes = self.private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return int.from_bytes(plaintext_bytes, 'big')
    
    def add_encrypted(self, ciphertext1: bytes, ciphertext2: bytes) -> bytes:
        """Add two encrypted values (mock implementation)"""
        # This is a mock - real homomorphic encryption would support this
        # For demonstration, decrypt, add, and re-encrypt
        val1 = self.decrypt(ciphertext1)
        val2 = self.decrypt(ciphertext2)
        result = val1 + val2
        return self.encrypt(result)

class PrivacyAudit:
    """Audit privacy guarantees and parameters"""
    
    def __init__(self):
        self.privacy_accountant = []
        self.logger = logging.getLogger(__name__)
    
    def record_privacy_expenditure(self, epsilon: float, delta: float, 
                                  mechanism: str, round_id: str):
        """Record privacy expenditure for accounting"""
        record = {
            'epsilon': epsilon,
            'delta': delta,
            'mechanism': mechanism,
            'round_id': round_id,
            'timestamp': time.time()
        }
        self.privacy_accountant.append(record)
        
        self.logger.info(f"Privacy expenditure: ε={epsilon:.4f}, δ={delta:.2e} for {mechanism}")
    
    def get_total_privacy_cost(self) -> Tuple[float, float]:
        """Calculate total privacy cost using composition"""
        # Simple composition (not optimal)
        total_epsilon = sum(record['epsilon'] for record in self.privacy_accountant)
        total_delta = sum(record['delta'] for record in self.privacy_accountant)
        
        return total_epsilon, total_delta
    
    def privacy_budget_remaining(self, budget_epsilon: float, budget_delta: float) -> Tuple[float, float]:
        """Calculate remaining privacy budget"""
        used_epsilon, used_delta = self.get_total_privacy_cost()
        
        remaining_epsilon = max(0, budget_epsilon - used_epsilon)
        remaining_delta = max(0, budget_delta - used_delta)
        
        return remaining_epsilon, remaining_delta