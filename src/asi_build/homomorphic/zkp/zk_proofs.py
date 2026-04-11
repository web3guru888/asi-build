"""Zero-knowledge proof implementations."""

import hashlib
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class ZKProofSystem(ABC):
    """Abstract base for zero-knowledge proof systems."""

    @abstractmethod
    def prove(self, statement: Any, witness: Any) -> Dict[str, Any]:
        """Generate a zero-knowledge proof."""
        pass

    @abstractmethod
    def verify(self, statement: Any, proof: Dict[str, Any]) -> bool:
        """Verify a zero-knowledge proof."""
        pass


class SchnorrProof(ZKProofSystem):
    """Schnorr proof of knowledge of discrete logarithm."""

    def __init__(self, prime: int = 2**31 - 1, generator: int = 2):
        self.prime = prime
        self.generator = generator

    def prove(self, statement: int, witness: int) -> Dict[str, Any]:
        """Prove knowledge of discrete log."""
        # statement = g^witness mod p
        if pow(self.generator, witness, self.prime) != statement:
            raise ValueError("Invalid witness for statement")

        # Commitment phase
        r = random.randint(1, self.prime - 1)
        commitment = pow(self.generator, r, self.prime)

        # Challenge phase (Fiat-Shamir)
        challenge_input = f"{statement}_{commitment}".encode()
        challenge = int(hashlib.sha256(challenge_input).hexdigest(), 16) % (self.prime - 1)

        # Response phase
        response = (r + challenge * witness) % (self.prime - 1)

        return {"commitment": commitment, "challenge": challenge, "response": response}

    def verify(self, statement: int, proof: Dict[str, Any]) -> bool:
        """Verify Schnorr proof."""
        commitment = proof["commitment"]
        challenge = proof["challenge"]
        response = proof["response"]

        # Verify challenge
        challenge_input = f"{statement}_{commitment}".encode()
        expected_challenge = int(hashlib.sha256(challenge_input).hexdigest(), 16) % (self.prime - 1)

        if challenge != expected_challenge:
            return False

        # Verify equation: g^response = commitment * statement^challenge
        left = pow(self.generator, response, self.prime)
        right = (commitment * pow(statement, challenge, self.prime)) % self.prime

        return left == right


class RangeProof(ZKProofSystem):
    """Zero-knowledge range proof."""

    def __init__(self, prime: int = 2**31 - 1):
        self.prime = prime
        self.generator = 2

    def prove(self, statement: int, witness: Tuple[int, int, int]) -> Dict[str, Any]:
        """Prove value is in range [min_val, max_val]."""
        value, min_val, max_val = witness

        if not (min_val <= value <= max_val):
            raise ValueError("Value not in specified range")

        # Simple range proof using bit decomposition
        range_size = max_val - min_val
        adjusted_value = value - min_val

        # Decompose into bits
        bits = []
        temp = adjusted_value
        for i in range(range_size.bit_length()):
            bits.append(temp & 1)
            temp >>= 1

        # Commit to each bit
        commitments = []
        randomness = []

        for bit in bits:
            r = random.randint(1, self.prime - 1)
            # Pedersen commitment
            h = pow(self.generator, 3, self.prime)  # Second generator
            commit = (pow(self.generator, bit, self.prime) * pow(h, r, self.prime)) % self.prime
            commitments.append(commit)
            randomness.append(r)

        return {
            "commitments": commitments,
            "randomness": randomness,
            "bits": bits,
            "range": (min_val, max_val),
        }

    def verify(self, statement: int, proof: Dict[str, Any]) -> bool:
        """Verify range proof."""
        commitments = proof["commitments"]
        bits = proof["bits"]
        randomness = proof["randomness"]
        min_val, max_val = proof["range"]

        # Verify bit commitments
        h = pow(self.generator, 3, self.prime)

        for bit, commit, r in zip(bits, commitments, randomness):
            expected = (pow(self.generator, bit, self.prime) * pow(h, r, self.prime)) % self.prime
            if commit != expected:
                return False

            # Verify bit is 0 or 1
            if bit not in [0, 1]:
                return False

        # Verify range
        reconstructed = sum(bit * (2**i) for i, bit in enumerate(bits))
        actual_value = reconstructed + min_val

        return min_val <= actual_value <= max_val and actual_value == statement
