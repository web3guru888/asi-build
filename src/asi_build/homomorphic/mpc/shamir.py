"""Shamir Secret Sharing implementation."""

import random
from typing import List, Tuple
from .protocols import MPCShare

class ShamirSecretSharing:
    """Shamir Secret Sharing implementation."""
    
    def __init__(self, threshold: int, num_parties: int, prime: int = 2**31 - 1):
        self.threshold = threshold
        self.num_parties = num_parties
        self.prime = prime
    
    def share_secret(self, secret: int) -> List[MPCShare]:
        """Share a secret using Shamir's method."""
        coeffs = [secret] + [random.randint(0, self.prime-1) for _ in range(self.threshold-1)]
        
        shares = []
        for i in range(1, self.num_parties + 1):
            share_value = sum(coeff * (i ** j) for j, coeff in enumerate(coeffs)) % self.prime
            shares.append(MPCShare(i-1, share_value, self.threshold-1, self.prime))
        
        return shares
    
    def reconstruct_secret(self, shares: List[MPCShare]) -> int:
        """Reconstruct secret from shares using Lagrange interpolation."""
        if len(shares) < self.threshold:
            raise ValueError("Insufficient shares")
        
        secret = 0
        for i, share in enumerate(shares[:self.threshold]):
            xi = share.party_id + 1
            numerator = 1
            denominator = 1
            
            for j, other_share in enumerate(shares[:self.threshold]):
                if i != j:
                    xj = other_share.party_id + 1
                    numerator = (numerator * (-xj)) % self.prime
                    denominator = (denominator * (xi - xj)) % self.prime
            
            lagrange_coeff = (numerator * pow(denominator, self.prime-2, self.prime)) % self.prime
            secret = (secret + share.share_value * lagrange_coeff) % self.prime
        
        return secret