"""Distributed key generation protocols."""

import random
from typing import Any, Dict, List, Tuple


class DistributedKeyGeneration:
    """Distributed key generation for threshold schemes."""

    def __init__(self, threshold: int, num_parties: int, prime: int = 2**31 - 1):
        self.threshold = threshold
        self.num_parties = num_parties
        self.prime = prime

    def generate_distributed_key(self) -> Dict[str, Any]:
        """Generate keys in distributed manner."""
        # Each party generates their own polynomial
        party_polynomials = []

        for party_id in range(self.num_parties):
            # Generate random polynomial coefficients
            coeffs = [random.randint(0, self.prime - 1) for _ in range(self.threshold)]
            party_polynomials.append(coeffs)

        # Each party computes shares for all other parties
        shares_matrix = []
        for i in range(self.num_parties):
            party_shares = []
            for j in range(self.num_parties):
                # Evaluate party i's polynomial at point j+1
                share_value = (
                    sum(coeffs[k] * ((j + 1) ** k) for k, coeffs in enumerate(party_polynomials[i]))
                    % self.prime
                )
                party_shares.append(share_value)
            shares_matrix.append(party_shares)

        # Each party combines shares they received
        final_shares = []
        for j in range(self.num_parties):
            combined_share = sum(shares_matrix[i][j] for i in range(self.num_parties)) % self.prime
            final_shares.append((j + 1, combined_share))

        # Public key is sum of all constant terms
        public_key = sum(poly[0] for poly in party_polynomials) % self.prime

        return {
            "public_key": public_key,
            "private_shares": final_shares,
            "verification_info": self._generate_verification_info(party_polynomials),
        }

    def _generate_verification_info(self, polynomials: List[List[int]]) -> List[List[int]]:
        """Generate verification information for key generation."""
        # Generate commitments to polynomial coefficients
        generator = 2
        verification_info = []

        for poly in polynomials:
            commitments = []
            for coeff in poly:
                commitment = pow(generator, coeff, self.prime)
                commitments.append(commitment)
            verification_info.append(commitments)

        return verification_info

    def verify_share(self, party_id: int, share: int, verification_info: List[List[int]]) -> bool:
        """Verify that a share is valid."""
        generator = 2

        # Compute expected share commitment
        expected_commitment = 1
        for i, commitments in enumerate(verification_info):
            party_contribution = 1
            for j, commitment in enumerate(commitments):
                party_contribution = (
                    party_contribution * pow(commitment, (party_id**j), self.prime)
                ) % self.prime
            expected_commitment = (expected_commitment * party_contribution) % self.prime

        # Compare with actual share commitment
        actual_commitment = pow(generator, share, self.prime)

        return expected_commitment == actual_commitment
