"""Multi-party PSI for more than two parties."""

import hashlib
import random
from typing import Dict, List, Set


class MultiPartyPSI:
    """Multi-party Private Set Intersection."""

    def __init__(self, num_parties: int, prime: int = 2**31 - 1):
        self.num_parties = num_parties
        self.prime = prime
        self.generator = 2

    def compute_intersection(self, party_sets: List[Set[str]]) -> Set[str]:
        """Compute intersection among multiple parties."""
        if len(party_sets) != self.num_parties:
            raise ValueError("Number of sets must match number of parties")

        # Generate secrets for each party
        secrets = [random.randint(1, self.prime - 1) for _ in range(self.num_parties)]

        # Each party encrypts their set
        encrypted_sets = []
        for i, party_set in enumerate(party_sets):
            encrypted_set = {}
            for item in party_set:
                h_item = int(hashlib.sha256(item.encode()).hexdigest(), 16) % self.prime

                # Apply all secrets in sequence
                encrypted = h_item
                for j in range(self.num_parties):
                    encrypted = pow(encrypted, secrets[j], self.prime)

                encrypted_set[encrypted] = item

            encrypted_sets.append(encrypted_set)

        # Find common encrypted values
        common_encrypted = set(encrypted_sets[0].keys())
        for encrypted_set in encrypted_sets[1:]:
            common_encrypted = common_encrypted.intersection(set(encrypted_set.keys()))

        # Return original items
        intersection = set()
        for enc_val in common_encrypted:
            intersection.add(encrypted_sets[0][enc_val])

        return intersection
