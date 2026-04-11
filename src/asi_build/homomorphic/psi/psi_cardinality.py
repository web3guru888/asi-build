"""PSI Cardinality - compute only intersection size."""

import hashlib
import random
from typing import Set


class PSICardinality:
    """Private Set Intersection Cardinality protocol."""

    def __init__(self, prime: int = 2**31 - 1):
        self.prime = prime
        self.generator = 2

    def compute_intersection_size(self, set_a: Set[str], set_b: Set[str]) -> int:
        """Compute only the size of intersection without revealing elements."""
        # Use similar DH-based approach but only return count

        a_secret = random.randint(1, self.prime - 1)
        b_secret = random.randint(1, self.prime - 1)

        # Encrypt sets
        a_encrypted = set()
        for item in set_a:
            h_x = int(hashlib.sha256(item.encode()).hexdigest(), 16) % self.prime
            encrypted = pow(h_x, a_secret, self.prime)
            a_encrypted.add(encrypted)

        b_encrypted = set()
        for item in set_b:
            h_y = int(hashlib.sha256(item.encode()).hexdigest(), 16) % self.prime
            encrypted = pow(h_y, b_secret, self.prime)
            b_encrypted.add(encrypted)

        # Double encrypt
        a_double = {pow(enc, b_secret, self.prime) for enc in a_encrypted}
        b_double = {pow(enc, a_secret, self.prime) for enc in b_encrypted}

        # Count intersection
        return len(a_double.intersection(b_double))
