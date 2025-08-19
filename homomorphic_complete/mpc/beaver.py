"""Beaver triples for efficient MPC multiplication."""

import random
from typing import List, Tuple
from .protocols import MPCShare

class BeaverTriples:
    """Generate and manage Beaver triples for efficient MPC."""
    
    def __init__(self, secret_sharing):
        self.secret_sharing = secret_sharing
        self.stored_triples = []
    
    def generate_triple(self) -> Tuple[List[MPCShare], List[MPCShare], List[MPCShare]]:
        """Generate a random Beaver triple (a, b, c) where c = a * b."""
        prime = self.secret_sharing.prime
        
        # Generate random a and b
        a = random.randint(0, prime - 1)
        b = random.randint(0, prime - 1)
        c = (a * b) % prime
        
        # Share the triple
        a_shares = self.secret_sharing.share_secret(a)
        b_shares = self.secret_sharing.share_secret(b)
        c_shares = self.secret_sharing.share_secret(c)
        
        return a_shares, b_shares, c_shares
    
    def precompute_triples(self, count: int):
        """Precompute multiple Beaver triples."""
        for _ in range(count):
            triple = self.generate_triple()
            self.stored_triples.append(triple)
    
    def get_triple(self) -> Tuple[List[MPCShare], List[MPCShare], List[MPCShare]]:
        """Get a precomputed Beaver triple."""
        if not self.stored_triples:
            return self.generate_triple()
        return self.stored_triples.pop(0)
    
    def multiply_with_beaver(self, x_shares: List[MPCShare], y_shares: List[MPCShare]) -> List[MPCShare]:
        """Multiply two shared values using a Beaver triple."""
        a_shares, b_shares, c_shares = self.get_triple()
        
        # Compute d = x - a and e = y - b (revealed)
        d_shares = [MPCShare(s.party_id, (s.share_value - a.share_value) % s.modulus, s.polynomial_degree, s.modulus) 
                   for s, a in zip(x_shares, a_shares)]
        e_shares = [MPCShare(s.party_id, (s.share_value - b.share_value) % s.modulus, s.polynomial_degree, s.modulus)
                   for s, b in zip(y_shares, b_shares)]
        
        # Reconstruct d and e
        d = self.secret_sharing.reconstruct_secret(d_shares)
        e = self.secret_sharing.reconstruct_secret(e_shares)
        
        # Compute result: xy = de + d*b + e*a + c
        result_shares = []
        for i, (a_share, b_share, c_share) in enumerate(zip(a_shares, b_shares, c_shares)):
            if i == 0:  # Only first party adds the constant de
                value = (d * e + d * b_share.share_value + e * a_share.share_value + c_share.share_value) % c_share.modulus
            else:
                value = (d * b_share.share_value + e * a_share.share_value + c_share.share_value) % c_share.modulus
            
            result_shares.append(MPCShare(i, value, c_share.polynomial_degree, c_share.modulus))
        
        return result_shares