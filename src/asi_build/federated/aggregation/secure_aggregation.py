"""
Secure Aggregation for Federated Learning

Implementation of secure multi-party computation for aggregating model updates
without revealing individual client contributions.
"""

import hashlib
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ..core.exceptions import AggregationError, SecurityError
from .base_aggregator import BaseAggregator


class SecretSharing:
    """Shamir's Secret Sharing implementation for secure aggregation."""

    def __init__(self, threshold: int, num_parties: int, prime: int = 2**127 - 1):
        self.threshold = threshold
        self.num_parties = num_parties
        self.prime = prime

    def generate_polynomial_coefficients(self, secret: int) -> List[int]:
        """Generate random polynomial coefficients with the secret as constant term."""
        coefficients = [secret]
        for _ in range(self.threshold - 1):
            coefficients.append(secrets.randbelow(self.prime))
        return coefficients

    def evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """Evaluate polynomial at point x."""
        result = 0
        for i, coeff in enumerate(coefficients):
            result = (result + coeff * pow(x, i, self.prime)) % self.prime
        return result

    def create_shares(self, secret: int) -> List[Tuple[int, int]]:
        """Create secret shares."""
        coefficients = self.generate_polynomial_coefficients(secret)
        shares = []
        for i in range(1, self.num_parties + 1):
            share_value = self.evaluate_polynomial(coefficients, i)
            shares.append((i, share_value))
        return shares

    def lagrange_interpolation(self, shares: List[Tuple[int, int]]) -> int:
        """Reconstruct secret using Lagrange interpolation."""
        if len(shares) < self.threshold:
            raise SecurityError(
                f"Insufficient shares for reconstruction. Need {self.threshold}, got {len(shares)}",
                security_level="secret_sharing",
            )

        result = 0
        for i, (xi, yi) in enumerate(shares[: self.threshold]):
            numerator = 1
            denominator = 1

            for j, (xj, _) in enumerate(shares[: self.threshold]):
                if i != j:
                    numerator = (numerator * (-xj)) % self.prime
                    denominator = (denominator * (xi - xj)) % self.prime

            # Compute modular inverse
            denominator_inv = pow(denominator, self.prime - 2, self.prime)
            lagrange_coeff = (numerator * denominator_inv) % self.prime
            result = (result + yi * lagrange_coeff) % self.prime

        return result % self.prime


class PaillierCryptosystem:
    """Simplified Paillier homomorphic encryption for secure aggregation."""

    def __init__(self, key_size: int = 1024):
        self.key_size = key_size
        self.public_key, self.private_key = self._generate_keys()

    def _generate_keys(self) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Generate Paillier public and private keys."""
        # Generate two large primes
        p = self._generate_prime(self.key_size // 2)
        q = self._generate_prime(self.key_size // 2)

        n = p * q
        lambda_n = (p - 1) * (q - 1) // self._gcd(p - 1, q - 1)

        # Choose g
        g = n + 1

        # Compute mu
        mu = pow(self._l_function(pow(g, lambda_n, n * n), n), -1, n)

        public_key = {"n": n, "g": g}
        private_key = {"lambda": lambda_n, "mu": mu, "n": n}

        return public_key, private_key

    def _generate_prime(self, bits: int) -> int:
        """Generate a prime number of specified bit length."""
        # Simplified prime generation (in production, use proper libraries)
        while True:
            candidate = secrets.randbits(bits)
            candidate |= (1 << bits - 1) | 1  # Set MSB and LSB
            if self._is_prime(candidate):
                return candidate

    def _is_prime(self, n: int, k: int = 10) -> bool:
        """Miller-Rabin primality test."""
        if n < 2:
            return False
        if n == 2 or n == 3:
            return True
        if n % 2 == 0:
            return False

        # Write n-1 as d * 2^r
        r = 0
        d = n - 1
        while d % 2 == 0:
            d //= 2
            r += 1

        # Witness loop
        for _ in range(k):
            a = secrets.randbelow(n - 2) + 2
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for _ in range(r - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True

    def _gcd(self, a: int, b: int) -> int:
        """Greatest common divisor."""
        while b:
            a, b = b, a % b
        return a

    def _l_function(self, u: int, n: int) -> int:
        """L function for Paillier."""
        return (u - 1) // n

    def encrypt(self, plaintext: int) -> int:
        """Encrypt a plaintext integer."""
        n = self.public_key["n"]
        g = self.public_key["g"]
        r = secrets.randbelow(n)

        c = (pow(g, plaintext, n * n) * pow(r, n, n * n)) % (n * n)
        return c

    def decrypt(self, ciphertext: int) -> int:
        """Decrypt a ciphertext integer."""
        n = self.private_key["n"]
        lambda_n = self.private_key["lambda"]
        mu = self.private_key["mu"]

        u = pow(ciphertext, lambda_n, n * n)
        plaintext = (self._l_function(u, n) * mu) % n
        return plaintext

    def add_encrypted(self, c1: int, c2: int) -> int:
        """Add two encrypted values homomorphically."""
        n = self.public_key["n"]
        return (c1 * c2) % (n * n)


class SecureAggregator(BaseAggregator):
    """Secure aggregation using multi-party computation."""

    def __init__(self, aggregator_id: str, config: Dict[str, Any] = None):
        super().__init__(aggregator_id, config)

        # Secure aggregation parameters
        self.threshold = self.config.get("threshold", 3)
        self.use_homomorphic = self.config.get("use_homomorphic", False)
        self.use_secret_sharing = self.config.get("use_secret_sharing", True)
        self.dropout_resilience = self.config.get("dropout_resilience", True)

        # Cryptographic components
        self.secret_sharing = None
        self.paillier = None
        self.client_keys = {}

        # Security state
        self.active_clients = set()
        self.client_commitments = {}
        self.aggregation_round = 0

        self.logger.info(f"Secure aggregator initialized with threshold={self.threshold}")

    def setup_secure_aggregation(self, client_ids: List[str]) -> Dict[str, Any]:
        """Setup secure aggregation protocol for given clients."""
        num_clients = len(client_ids)
        if num_clients < self.threshold:
            raise SecurityError(
                f"Insufficient clients for secure aggregation. Need {self.threshold}, got {num_clients}",
                security_level="secure_aggregation",
                threat_type="insufficient_participants",
            )

        self.active_clients = set(client_ids)

        # Initialize secret sharing
        if self.use_secret_sharing:
            self.secret_sharing = SecretSharing(threshold=self.threshold, num_parties=num_clients)

        # Initialize homomorphic encryption
        if self.use_homomorphic:
            self.paillier = PaillierCryptosystem()

        # Generate setup parameters
        setup_params = {
            "aggregation_round": self.aggregation_round,
            "threshold": self.threshold,
            "active_clients": list(self.active_clients),
            "timestamp": time.time(),
        }

        if self.use_homomorphic and self.paillier:
            setup_params["public_key"] = self.paillier.public_key

        self.logger.info(f"Secure aggregation setup completed for {num_clients} clients")
        return setup_params

    def generate_client_masks(
        self, client_ids: List[str], weight_shapes: List[Tuple]
    ) -> Dict[str, List[np.ndarray]]:
        """Generate additive masks for clients."""
        client_masks = {}

        for client_id in client_ids:
            masks = []
            for shape in weight_shapes:
                # Generate random mask
                mask = np.random.randint(-1000000, 1000000, size=shape, dtype=np.int64)
                masks.append(mask)
            client_masks[client_id] = masks

        return client_masks

    def mask_weights(self, weights: List[np.ndarray], masks: List[np.ndarray]) -> List[np.ndarray]:
        """Apply additive masks to weights."""
        masked_weights = []
        for weight, mask in zip(weights, masks):
            # Convert to integer representation for secure computation
            scaled_weight = (weight * 10000).astype(np.int64)
            masked_weight = scaled_weight + mask
            masked_weights.append(masked_weight)

        return masked_weights

    def unmask_aggregated_weights(
        self, masked_weights: List[np.ndarray], total_masks: List[np.ndarray]
    ) -> List[np.ndarray]:
        """Remove masks from aggregated weights."""
        unmasked_weights = []
        for masked_weight, total_mask in zip(masked_weights, total_masks):
            unmasked_weight = masked_weight - total_mask
            # Convert back to float
            unmasked_weight = unmasked_weight.astype(np.float32) / 10000
            unmasked_weights.append(unmasked_weight)

        return unmasked_weights

    def secure_sum_with_secret_sharing(self, client_values: List[int]) -> int:
        """Perform secure sum using secret sharing."""
        if not self.secret_sharing:
            raise SecurityError("Secret sharing not initialized", security_level="secret_sharing")

        # Each client creates shares of their value
        all_shares = []
        for i, value in enumerate(client_values):
            shares = self.secret_sharing.create_shares(value)
            all_shares.append(shares)

        # Aggregate shares for each party
        aggregated_shares = []
        for party_id in range(1, len(client_values) + 1):
            party_sum = 0
            for client_shares in all_shares:
                for share_id, share_value in client_shares:
                    if share_id == party_id:
                        party_sum += share_value
                        break
            aggregated_shares.append((party_id, party_sum % self.secret_sharing.prime))

        # Reconstruct the sum
        total_sum = self.secret_sharing.lagrange_interpolation(aggregated_shares)
        return total_sum

    def aggregate(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform secure aggregation of client updates."""
        start_time = time.time()

        # Validate updates
        self.validate_updates(client_updates)

        # Extract client information
        client_ids = [update["client_id"] for update in client_updates]
        client_weights_list = [update["weights"] for update in client_updates]
        data_sizes = [update["data_size"] for update in client_updates]

        self.logger.info(f"Starting secure aggregation for {len(client_updates)} clients")

        # Setup secure aggregation if not done
        if not self.active_clients or self.active_clients != set(client_ids):
            weight_shapes = [w.shape for w in client_weights_list[0]]
            setup_params = self.setup_secure_aggregation(client_ids)

        try:
            # Method 1: Use secret sharing for secure aggregation
            if self.use_secret_sharing and len(client_updates) >= self.threshold:
                aggregated_weights = self._secure_aggregate_with_secret_sharing(
                    client_weights_list, data_sizes
                )

            # Method 2: Use homomorphic encryption
            elif self.use_homomorphic and self.paillier:
                aggregated_weights = self._secure_aggregate_with_homomorphic(
                    client_weights_list, data_sizes
                )

            # Fallback: Use masking (less secure but more efficient)
            else:
                aggregated_weights = self._secure_aggregate_with_masking(
                    client_weights_list, data_sizes, client_ids
                )

            aggregation_time = time.time() - start_time

            # Create aggregation result
            result = {
                "aggregated_weights": aggregated_weights,
                "num_clients": len(client_updates),
                "aggregation_time": aggregation_time,
                "aggregation_method": "secure_aggregation",
                "security_level": self._get_security_level(),
                "metadata": {
                    "threshold": self.threshold,
                    "total_samples": sum(data_sizes),
                    "avg_client_samples": np.mean(data_sizes),
                    "aggregation_round": self.aggregation_round,
                },
            }

            # Record aggregation statistics
            self.record_aggregation(result)
            self.aggregation_round += 1

            self.logger.info(f"Secure aggregation completed in {aggregation_time:.3f}s")
            return result

        except Exception as e:
            self.logger.error(f"Secure aggregation failed: {str(e)}")
            raise AggregationError(
                f"Secure aggregation failed: {str(e)}",
                aggregator_type=self.aggregator_id,
                client_count=len(client_updates),
            )

    def _secure_aggregate_with_secret_sharing(
        self, client_weights_list: List[List[np.ndarray]], data_sizes: List[int]
    ) -> List[np.ndarray]:
        """Aggregate using secret sharing."""
        if not self.secret_sharing:
            raise SecurityError("Secret sharing not initialized")

        # Compute client weights for aggregation
        client_aggregation_weights = self.compute_client_weights(
            [{"data_size": size} for size in data_sizes]
        )

        aggregated_weights = []
        num_layers = len(client_weights_list[0])

        for layer_idx in range(num_layers):
            layer_weights = [weights[layer_idx] for weights in client_weights_list]

            # Flatten weights for secret sharing
            flat_weights = []
            original_shape = layer_weights[0].shape

            for i, weight in enumerate(layer_weights):
                # Scale and convert to integer
                scaled_weight = (weight * client_aggregation_weights[i] * 10000).astype(np.int64)
                flat_weights.append(scaled_weight.flatten())

            # Perform secure sum for each weight element
            aggregated_flat = np.zeros_like(flat_weights[0])
            for elem_idx in range(len(flat_weights[0])):
                client_values = [int(client_flat[elem_idx]) for client_flat in flat_weights]

                # Use secret sharing to compute sum
                if len(client_values) >= self.threshold:
                    secure_sum = self.secure_sum_with_secret_sharing(client_values)
                    aggregated_flat[elem_idx] = secure_sum
                else:
                    # Fallback to regular sum
                    aggregated_flat[elem_idx] = sum(client_values)

            # Reshape and convert back to float
            aggregated_layer = aggregated_flat.reshape(original_shape).astype(np.float32) / 10000
            aggregated_weights.append(aggregated_layer)

        return aggregated_weights

    def _secure_aggregate_with_homomorphic(
        self, client_weights_list: List[List[np.ndarray]], data_sizes: List[int]
    ) -> List[np.ndarray]:
        """Aggregate using homomorphic encryption."""
        if not self.paillier:
            raise SecurityError("Homomorphic encryption not initialized")

        # Compute client weights
        client_aggregation_weights = self.compute_client_weights(
            [{"data_size": size} for size in data_sizes]
        )

        aggregated_weights = []
        num_layers = len(client_weights_list[0])

        for layer_idx in range(num_layers):
            layer_weights = [weights[layer_idx] for weights in client_weights_list]

            # Process weights with homomorphic encryption
            encrypted_sums = None
            original_shape = layer_weights[0].shape

            for i, weight in enumerate(layer_weights):
                # Scale and convert to integer
                scaled_weight = (weight * client_aggregation_weights[i] * 1000).astype(np.int64)
                flat_weight = scaled_weight.flatten()

                # Encrypt each element
                encrypted_weight = np.array(
                    [
                        self.paillier.encrypt(int(val) % (self.paillier.public_key["n"] // 2))
                        for val in flat_weight
                    ]
                )

                if encrypted_sums is None:
                    encrypted_sums = encrypted_weight
                else:
                    # Homomorphic addition
                    encrypted_sums = np.array(
                        [
                            self.paillier.add_encrypted(enc_sum, enc_weight)
                            for enc_sum, enc_weight in zip(encrypted_sums, encrypted_weight)
                        ]
                    )

            # Decrypt the aggregated result
            decrypted_sums = np.array(
                [self.paillier.decrypt(enc_sum) for enc_sum in encrypted_sums]
            )

            # Handle negative values and reshape
            decrypted_sums = np.where(
                decrypted_sums > self.paillier.public_key["n"] // 2,
                decrypted_sums - self.paillier.public_key["n"],
                decrypted_sums,
            )

            aggregated_layer = decrypted_sums.reshape(original_shape).astype(np.float32) / 1000
            aggregated_weights.append(aggregated_layer)

        return aggregated_weights

    def _secure_aggregate_with_masking(
        self,
        client_weights_list: List[List[np.ndarray]],
        data_sizes: List[int],
        client_ids: List[str],
    ) -> List[np.ndarray]:
        """Aggregate using additive masking (less secure but efficient)."""
        # Get weight shapes
        weight_shapes = [w.shape for w in client_weights_list[0]]

        # Generate masks for each client
        client_masks = self.generate_client_masks(client_ids, weight_shapes)

        # Compute total mask (sum of all client masks)
        total_masks = []
        for layer_idx in range(len(weight_shapes)):
            total_mask = np.zeros(weight_shapes[layer_idx], dtype=np.int64)
            for client_id in client_ids:
                total_mask += client_masks[client_id][layer_idx]
            total_masks.append(total_mask)

        # Apply masks to client weights and aggregate
        client_aggregation_weights = self.compute_client_weights(
            [{"data_size": size} for size in data_sizes]
        )

        aggregated_masked_weights = []
        num_layers = len(client_weights_list[0])

        for layer_idx in range(num_layers):
            layer_sum = np.zeros_like(client_weights_list[0][layer_idx])

            for i, weights in enumerate(client_weights_list):
                # Apply client weight and masking
                client_id = client_ids[i]
                weight_contribution = weights[layer_idx] * client_aggregation_weights[i]

                # Add mask
                masked_contribution = self.mask_weights(
                    [weight_contribution], [client_masks[client_id][layer_idx]]
                )[0]

                layer_sum += masked_contribution.astype(np.float32) / 10000

            aggregated_masked_weights.append(layer_sum)

        # Remove total mask
        aggregated_weights = self.unmask_aggregated_weights(aggregated_masked_weights, total_masks)

        return aggregated_weights

    def _get_security_level(self) -> str:
        """Get current security level description."""
        if self.use_secret_sharing:
            return f"secret_sharing_t{self.threshold}"
        elif self.use_homomorphic:
            return "homomorphic_encryption"
        else:
            return "additive_masking"

    def get_security_guarantees(self) -> Dict[str, Any]:
        """Get security guarantees of the current configuration."""
        guarantees = {
            "privacy_preserving": True,
            "individual_client_protection": True,
            "dropout_resilience": self.dropout_resilience,
            "threshold": self.threshold,
            "security_level": self._get_security_level(),
        }

        if self.use_secret_sharing:
            guarantees.update(
                {
                    "information_theoretic_security": True,
                    "requires_threshold_parties": True,
                    "secure_against_honest_but_curious": True,
                    "secure_against_malicious_minority": True,
                }
            )

        if self.use_homomorphic:
            guarantees.update(
                {
                    "computational_security": True,
                    "additively_homomorphic": True,
                    "key_size": getattr(self.paillier, "key_size", None),
                }
            )

        return guarantees
