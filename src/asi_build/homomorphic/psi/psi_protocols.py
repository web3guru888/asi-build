"""Private Set Intersection protocol implementations."""

import hashlib
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set


class PSIProtocol(ABC):
    """Abstract base class for PSI protocols."""

    @abstractmethod
    def compute_intersection(self, set_a: Set[str], set_b: Set[str]) -> Set[str]:
        """Compute private set intersection."""
        pass


class DHBasedPSI(PSIProtocol):
    """Diffie-Hellman based PSI protocol."""

    def __init__(self, prime: int = 2**31 - 1):
        self.prime = prime
        self.generator = 2

    def compute_intersection(self, set_a: Set[str], set_b: Set[str]) -> Set[str]:
        """Compute PSI using DH-based protocol."""
        # Party A's secret key
        a_secret = random.randint(1, self.prime - 1)

        # Party A computes H(x)^a for each x in set_a
        a_encrypted = {}
        for item in set_a:
            h_x = int(hashlib.sha256(item.encode()).hexdigest(), 16) % self.prime
            encrypted = pow(h_x, a_secret, self.prime)
            a_encrypted[encrypted] = item

        # Party B's secret key
        b_secret = random.randint(1, self.prime - 1)

        # Party B computes H(y)^b for each y in set_b
        b_encrypted = {}
        for item in set_b:
            h_y = int(hashlib.sha256(item.encode()).hexdigest(), 16) % self.prime
            encrypted = pow(h_y, b_secret, self.prime)
            b_encrypted[encrypted] = item

        # Exchange and re-encrypt
        a_double_encrypted = {}
        for enc_val in a_encrypted:
            double_enc = pow(enc_val, b_secret, self.prime)
            a_double_encrypted[double_enc] = a_encrypted[enc_val]

        b_double_encrypted = {}
        for enc_val in b_encrypted:
            double_enc = pow(enc_val, a_secret, self.prime)
            b_double_encrypted[double_enc] = b_encrypted[enc_val]

        # Find intersection
        intersection = set()
        for enc_val in a_double_encrypted:
            if enc_val in b_double_encrypted:
                intersection.add(a_double_encrypted[enc_val])

        return intersection


class OTBasedPSI(PSIProtocol):
    """Oblivious Transfer based PSI protocol."""

    def __init__(self):
        self.prime = 2**31 - 1

    def compute_intersection(self, set_a: Set[str], set_b: Set[str]) -> Set[str]:
        """Compute PSI using OT-based protocol (simplified)."""
        # Simplified implementation
        # Real OT-based PSI is more complex

        intersection = set()

        # Use hash-based comparison as placeholder
        for item_a in set_a:
            hash_a = hashlib.sha256(item_a.encode()).hexdigest()
            for item_b in set_b:
                hash_b = hashlib.sha256(item_b.encode()).hexdigest()
                if hash_a == hash_b:
                    intersection.add(item_a)

        return intersection
