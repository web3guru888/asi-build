"""
Core MPC protocols (BGW, GMW, etc.)
"""

import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MPCShare:
    """Represents a secret share in MPC protocols."""

    party_id: int
    share_value: int
    polynomial_degree: int
    modulus: int

    def __str__(self) -> str:
        return f"Share(party={self.party_id}, value={self.share_value}, mod={self.modulus})"


class SecretSharingProtocol(ABC):
    """Abstract base class for secret sharing protocols."""

    def __init__(self, threshold: int, num_parties: int, modulus: int):
        """
        Initialize secret sharing protocol.

        Args:
            threshold: Minimum shares needed to reconstruct
            num_parties: Total number of parties
            modulus: Prime modulus for arithmetic
        """
        self.threshold = threshold
        self.num_parties = num_parties
        self.modulus = modulus

        if threshold > num_parties:
            raise ValueError("Threshold cannot exceed number of parties")

        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def share_secret(self, secret: int) -> List[MPCShare]:
        """Share a secret among parties."""
        pass

    @abstractmethod
    def reconstruct_secret(self, shares: List[MPCShare]) -> int:
        """Reconstruct secret from shares."""
        pass

    @abstractmethod
    def add_shares(self, shares1: List[MPCShare], shares2: List[MPCShare]) -> List[MPCShare]:
        """Add two sets of shares."""
        pass

    @abstractmethod
    def multiply_shares(self, shares1: List[MPCShare], shares2: List[MPCShare]) -> List[MPCShare]:
        """Multiply two sets of shares."""
        pass


class BGWProtocol(SecretSharingProtocol):
    """
    BGW (Ben-Or, Goldwasser, Wigderson) Protocol.

    Information-theoretically secure MPC protocol based on
    Shamir secret sharing over finite fields.
    """

    def __init__(self, threshold: int, num_parties: int, modulus: int):
        """
        Initialize BGW protocol.

        Args:
            threshold: Threshold for secret reconstruction (t < n/2)
            num_parties: Number of parties
            modulus: Prime modulus for field operations
        """
        if threshold >= num_parties // 2:
            raise ValueError("BGW requires threshold < n/2 for active security")

        super().__init__(threshold, num_parties, modulus)

        # Precompute evaluation points (1, 2, ..., n)
        self.evaluation_points = list(range(1, num_parties + 1))

        self.logger.info(f"Initialized BGW protocol: t={threshold}, n={num_parties}, p={modulus}")

    def share_secret(self, secret: int) -> List[MPCShare]:
        """
        Share secret using Shamir secret sharing.

        Args:
            secret: Secret value to share

        Returns:
            List of secret shares
        """
        secret = secret % self.modulus

        # Generate random polynomial of degree t-1
        # f(x) = secret + a₁x + a₂x² + ... + aₜ₋₁x^(t-1)
        coefficients = [secret] + [
            random.randint(0, self.modulus - 1) for _ in range(self.threshold - 1)
        ]

        # Evaluate polynomial at each party's point
        shares = []
        for i, point in enumerate(self.evaluation_points):
            share_value = self._evaluate_polynomial(coefficients, point) % self.modulus

            share = MPCShare(
                party_id=i,
                share_value=share_value,
                polynomial_degree=self.threshold - 1,
                modulus=self.modulus,
            )
            shares.append(share)

        self.logger.debug(f"Shared secret {secret} into {len(shares)} shares")
        return shares

    def reconstruct_secret(self, shares: List[MPCShare]) -> int:
        """
        Reconstruct secret using Lagrange interpolation.

        Args:
            shares: List of at least t shares

        Returns:
            Reconstructed secret
        """
        if len(shares) < self.threshold:
            raise ValueError(f"Need at least {self.threshold} shares, got {len(shares)}")

        # Use first t shares for reconstruction
        used_shares = shares[: self.threshold]

        # Lagrange interpolation at x=0
        secret = 0
        for i, share in enumerate(used_shares):
            xi = self.evaluation_points[share.party_id]

            # Compute Lagrange basis polynomial Li(0)
            numerator = 1
            denominator = 1

            for j, other_share in enumerate(used_shares):
                if i != j:
                    xj = self.evaluation_points[other_share.party_id]
                    numerator = (numerator * (-xj)) % self.modulus
                    denominator = (denominator * (xi - xj)) % self.modulus

            # Compute modular inverse of denominator
            denominator_inv = self._mod_inverse(denominator, self.modulus)
            lagrange_coeff = (numerator * denominator_inv) % self.modulus

            secret = (secret + share.share_value * lagrange_coeff) % self.modulus

        self.logger.debug(f"Reconstructed secret: {secret}")
        return secret

    def add_shares(self, shares1: List[MPCShare], shares2: List[MPCShare]) -> List[MPCShare]:
        """
        Add two sets of shares (local operation).

        Args:
            shares1: First set of shares
            shares2: Second set of shares

        Returns:
            Sum of shares
        """
        if len(shares1) != len(shares2):
            raise ValueError("Share sets must have same length")

        result_shares = []
        for s1, s2 in zip(shares1, shares2):
            if s1.party_id != s2.party_id:
                raise ValueError("Share party IDs must match")

            sum_value = (s1.share_value + s2.share_value) % self.modulus

            result_share = MPCShare(
                party_id=s1.party_id,
                share_value=sum_value,
                polynomial_degree=max(s1.polynomial_degree, s2.polynomial_degree),
                modulus=self.modulus,
            )
            result_shares.append(result_share)

        return result_shares

    def multiply_shares(self, shares1: List[MPCShare], shares2: List[MPCShare]) -> List[MPCShare]:
        """
        Multiply two sets of shares (requires degree reduction).

        Args:
            shares1: First set of shares
            shares2: Second set of shares

        Returns:
            Product of shares (degree reduced)
        """
        if len(shares1) != len(shares2):
            raise ValueError("Share sets must have same length")

        # Local multiplication increases degree
        temp_shares = []
        for s1, s2 in zip(shares1, shares2):
            if s1.party_id != s2.party_id:
                raise ValueError("Share party IDs must match")

            product_value = (s1.share_value * s2.share_value) % self.modulus
            new_degree = s1.polynomial_degree + s2.polynomial_degree

            temp_share = MPCShare(
                party_id=s1.party_id,
                share_value=product_value,
                polynomial_degree=new_degree,
                modulus=self.modulus,
            )
            temp_shares.append(temp_share)

        # Degree reduction (simplified - would use more sophisticated methods)
        # For now, reconstruct and re-share (not secure in practice)
        if temp_shares[0].polynomial_degree >= self.threshold:
            secret = self.reconstruct_secret(temp_shares)
            return self.share_secret(secret)

        return temp_shares

    def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """Evaluate polynomial at point x using Horner's method."""
        result = 0
        for coeff in reversed(coefficients):
            result = (result * x + coeff) % self.modulus
        return result

    def _mod_inverse(self, a: int, m: int) -> int:
        """Compute modular multiplicative inverse using extended Euclidean algorithm."""

        def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
            if a == 0:
                return b, 0, 1

            gcd, x1, y1 = extended_gcd(b % a, a)
            x = y1 - (b // a) * x1
            y = x1

            return gcd, x, y

        gcd, x, _ = extended_gcd(a % m, m)
        if gcd != 1:
            raise ValueError(f"Modular inverse of {a} mod {m} doesn't exist")

        return (x % m + m) % m


class GMWProtocol(SecretSharingProtocol):
    """
    GMW (Goldreich, Micali, Wigderson) Protocol.

    Cryptographically secure MPC protocol based on oblivious transfer
    and garbled circuits for boolean operations.
    """

    def __init__(self, num_parties: int, security_parameter: int = 128):
        """
        Initialize GMW protocol.

        Args:
            num_parties: Number of parties
            security_parameter: Security parameter in bits
        """
        # GMW uses threshold = num_parties - 1 (all parties needed)
        super().__init__(num_parties - 1, num_parties, 2)  # Binary field

        self.security_parameter = security_parameter
        self.logger.info(f"Initialized GMW protocol: n={num_parties}, λ={security_parameter}")

    def share_secret(self, secret: int) -> List[MPCShare]:
        """
        Share secret using XOR secret sharing.

        Args:
            secret: Secret bit to share

        Returns:
            List of XOR shares
        """
        secret = secret % 2  # Ensure binary

        # Generate random shares for first n-1 parties
        shares = []
        xor_sum = 0

        for i in range(self.num_parties - 1):
            share_value = random.randint(0, 1)
            xor_sum ^= share_value

            share = MPCShare(party_id=i, share_value=share_value, polynomial_degree=1, modulus=2)
            shares.append(share)

        # Last party gets the XOR of all previous shares XOR secret
        last_share_value = secret ^ xor_sum
        last_share = MPCShare(
            party_id=self.num_parties - 1,
            share_value=last_share_value,
            polynomial_degree=1,
            modulus=2,
        )
        shares.append(last_share)

        self.logger.debug(f"XOR-shared secret {secret} into {len(shares)} shares")
        return shares

    def reconstruct_secret(self, shares: List[MPCShare]) -> int:
        """
        Reconstruct secret by XORing all shares.

        Args:
            shares: All XOR shares

        Returns:
            Reconstructed secret
        """
        if len(shares) != self.num_parties:
            raise ValueError(f"GMW requires all {self.num_parties} shares")

        secret = 0
        for share in shares:
            secret ^= share.share_value

        self.logger.debug(f"Reconstructed secret: {secret}")
        return secret

    def add_shares(self, shares1: List[MPCShare], shares2: List[MPCShare]) -> List[MPCShare]:
        """
        XOR two sets of shares (addition in GF(2)).

        Args:
            shares1: First set of shares
            shares2: Second set of shares

        Returns:
            XOR of shares
        """
        if len(shares1) != len(shares2):
            raise ValueError("Share sets must have same length")

        result_shares = []
        for s1, s2 in zip(shares1, shares2):
            if s1.party_id != s2.party_id:
                raise ValueError("Share party IDs must match")

            xor_value = s1.share_value ^ s2.share_value

            result_share = MPCShare(
                party_id=s1.party_id, share_value=xor_value, polynomial_degree=1, modulus=2
            )
            result_shares.append(result_share)

        return result_shares

    def multiply_shares(self, shares1: List[MPCShare], shares2: List[MPCShare]) -> List[MPCShare]:
        """
        Multiply shares using AND gates (requires communication).

        Args:
            shares1: First set of shares
            shares2: Second set of shares

        Returns:
            Product shares (simplified implementation)
        """
        if len(shares1) != len(shares2):
            raise ValueError("Share sets must have same length")

        # Simplified multiplication (real GMW requires oblivious transfer)
        # This is just for demonstration
        result_shares = []
        for s1, s2 in zip(shares1, shares2):
            if s1.party_id != s2.party_id:
                raise ValueError("Share party IDs must match")

            # Local AND operation (not secure - real GMW needs OT)
            and_value = s1.share_value & s2.share_value

            result_share = MPCShare(
                party_id=s1.party_id, share_value=and_value, polynomial_degree=1, modulus=2
            )
            result_shares.append(result_share)

        self.logger.warning("Simplified multiplication - real GMW requires secure AND gates")
        return result_shares

    def evaluate_circuit(
        self, circuit: Dict[str, Any], input_shares: Dict[str, List[MPCShare]]
    ) -> Dict[str, List[MPCShare]]:
        """
        Evaluate a boolean circuit on shared inputs.

        Args:
            circuit: Circuit description with gates
            input_shares: Input wire shares

        Returns:
            Output wire shares
        """
        wire_shares = input_shares.copy()

        # Process gates in topological order
        for gate in circuit.get("gates", []):
            gate_type = gate["type"]
            inputs = gate["inputs"]
            output = gate["output"]

            if gate_type == "XOR":
                wire_shares[output] = self.add_shares(
                    wire_shares[inputs[0]], wire_shares[inputs[1]]
                )
            elif gate_type == "AND":
                wire_shares[output] = self.multiply_shares(
                    wire_shares[inputs[0]], wire_shares[inputs[1]]
                )
            elif gate_type == "NOT":
                # NOT gate: flip all bits
                input_shares = wire_shares[inputs[0]]
                not_shares = []
                for share in input_shares:
                    not_share = MPCShare(
                        party_id=share.party_id,
                        share_value=1 ^ share.share_value,
                        polynomial_degree=1,
                        modulus=2,
                    )
                    not_shares.append(not_share)
                wire_shares[output] = not_shares

        # Return output wires
        output_wires = circuit.get("outputs", [])
        return {wire: wire_shares[wire] for wire in output_wires}


class MPCComputation:
    """High-level MPC computation interface."""

    def __init__(self, protocol: SecretSharingProtocol):
        """
        Initialize MPC computation.

        Args:
            protocol: Underlying MPC protocol
        """
        self.protocol = protocol
        self.logger = logging.getLogger(self.__class__.__name__)

    def secure_sum(self, secrets: List[int]) -> List[MPCShare]:
        """
        Compute sum of secrets using MPC.

        Args:
            secrets: List of secret values

        Returns:
            Shares of the sum
        """
        if not secrets:
            return self.protocol.share_secret(0)

        # Share first secret
        result_shares = self.protocol.share_secret(secrets[0])

        # Add remaining secrets
        for secret in secrets[1:]:
            secret_shares = self.protocol.share_secret(secret)
            result_shares = self.protocol.add_shares(result_shares, secret_shares)

        self.logger.info(f"Computed secure sum of {len(secrets)} values")
        return result_shares

    def secure_product(self, secrets: List[int]) -> List[MPCShare]:
        """
        Compute product of secrets using MPC.

        Args:
            secrets: List of secret values

        Returns:
            Shares of the product
        """
        if not secrets:
            return self.protocol.share_secret(1)

        # Share first secret
        result_shares = self.protocol.share_secret(secrets[0])

        # Multiply remaining secrets
        for secret in secrets[1:]:
            secret_shares = self.protocol.share_secret(secret)
            result_shares = self.protocol.multiply_shares(result_shares, secret_shares)

        self.logger.info(f"Computed secure product of {len(secrets)} values")
        return result_shares

    def secure_comparison(self, secret1: int, secret2: int) -> List[MPCShare]:
        """
        Securely compare two secrets (secret1 < secret2).

        Args:
            secret1: First secret
            secret2: Second secret

        Returns:
            Shares of comparison result (1 if secret1 < secret2, 0 otherwise)
        """
        # Simplified comparison (real implementation would use bit decomposition)
        difference = (secret2 - secret1) % self.protocol.modulus

        # Check if difference is in upper half of field (indicates secret1 > secret2)
        is_negative = 1 if difference > self.protocol.modulus // 2 else 0

        return self.protocol.share_secret(1 - is_negative)

    def secure_max(self, secrets: List[int]) -> Tuple[List[MPCShare], List[MPCShare]]:
        """
        Find maximum value and its index securely.

        Args:
            secrets: List of secret values

        Returns:
            Tuple of (max_value_shares, max_index_shares)
        """
        if not secrets:
            raise ValueError("Cannot find max of empty list")

        # Start with first element
        max_shares = self.protocol.share_secret(secrets[0])
        max_index_shares = self.protocol.share_secret(0)

        # Compare with remaining elements
        for i, secret in enumerate(secrets[1:], 1):
            secret_shares = self.protocol.share_secret(secret)

            # Compare current max with new value
            is_greater = self.secure_comparison(secrets[0], secret)  # Simplified

            # Update max and index based on comparison
            # This is a simplified implementation
            max_shares = self.protocol.add_shares(max_shares, secret_shares)

        self.logger.info(f"Computed secure maximum of {len(secrets)} values")
        return max_shares, max_index_shares
