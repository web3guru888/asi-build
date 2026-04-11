"""Threshold encryption schemes."""

import random
from typing import Any, Dict, List, Tuple


class ThresholdEncryption:
    """Threshold encryption based on ElGamal."""

    def __init__(self, threshold: int, num_parties: int, prime: int = 2**31 - 1):
        self.threshold = threshold
        self.num_parties = num_parties
        self.prime = prime
        self.generator = 2

    def setup(self) -> Dict[str, Any]:
        """Setup threshold encryption system."""
        # Generate shared secret key
        secret_key = random.randint(1, self.prime - 1)

        # Share secret key using Shamir's secret sharing
        shares = self._share_secret(secret_key)

        # Public key
        public_key = pow(self.generator, secret_key, self.prime)

        return {"public_key": public_key, "private_shares": shares, "threshold": self.threshold}

    def encrypt(self, message: int, public_key: int) -> Tuple[int, int]:
        """Encrypt message using public key."""
        # ElGamal encryption
        k = random.randint(1, self.prime - 1)

        c1 = pow(self.generator, k, self.prime)
        c2 = (message * pow(public_key, k, self.prime)) % self.prime

        return (c1, c2)

    def partial_decrypt(
        self, ciphertext: Tuple[int, int], share: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Perform partial decryption with a key share."""
        c1, c2 = ciphertext
        party_id, share_value = share

        # Partial decryption: c1^share_value
        partial_result = pow(c1, share_value, self.prime)

        return (party_id, partial_result)

    def combine_partial_decryptions(
        self, partials: List[Tuple[int, int]], ciphertext: Tuple[int, int]
    ) -> int:
        """Combine partial decryptions to recover message."""
        if len(partials) < self.threshold:
            raise ValueError("Insufficient partial decryptions")

        c1, c2 = ciphertext

        # Use Lagrange interpolation to combine partials
        combined_partial = 1

        for i, (party_id, partial_result) in enumerate(partials[: self.threshold]):
            # Compute Lagrange coefficient
            lagrange_coeff = 1

            for j, (other_party_id, _) in enumerate(partials[: self.threshold]):
                if i != j:
                    numerator = other_party_id
                    denominator = other_party_id - party_id

                    # Modular division
                    denominator_inv = pow(denominator, self.prime - 2, self.prime)
                    lagrange_coeff = (lagrange_coeff * numerator * denominator_inv) % self.prime

            # Apply Lagrange coefficient to partial result
            combined_partial = (
                combined_partial * pow(partial_result, lagrange_coeff, self.prime)
            ) % self.prime

        # Recover message: c2 / combined_partial
        combined_partial_inv = pow(combined_partial, self.prime - 2, self.prime)
        message = (c2 * combined_partial_inv) % self.prime

        return message

    def _share_secret(self, secret: int) -> List[Tuple[int, int]]:
        """Share secret using Shamir's secret sharing."""
        # Generate polynomial coefficients
        coeffs = [secret] + [random.randint(0, self.prime - 1) for _ in range(self.threshold - 1)]

        # Generate shares
        shares = []
        for party_id in range(1, self.num_parties + 1):
            share_value = sum(coeff * (party_id**i) for i, coeff in enumerate(coeffs)) % self.prime
            shares.append((party_id, share_value))

        return shares
