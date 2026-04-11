"""Oblivious Transfer protocols."""

import random
from typing import List, Tuple


class ObliviousTransfer:
    """1-out-of-2 Oblivious Transfer implementation."""

    def __init__(self, prime: int = 2**31 - 1):
        self.prime = prime
        self.generator = 2  # Generator for the group

    def ot_send_setup(self, m0: int, m1: int) -> Tuple[int, int, int, int]:
        """Sender setup for 1-out-of-2 OT."""
        # Generate random values
        a = random.randint(1, self.prime - 1)
        alpha = pow(self.generator, a, self.prime)

        # Choose random x0, x1
        x0 = random.randint(0, self.prime - 1)
        x1 = random.randint(0, self.prime - 1)

        return alpha, x0, x1, a

    def ot_receive_query(self, alpha: int, choice_bit: int) -> Tuple[int, int]:
        """Receiver creates query for chosen bit."""
        # Generate random b
        b = random.randint(1, self.prime - 1)

        if choice_bit == 0:
            beta = pow(self.generator, b, self.prime)
        else:
            beta = (alpha * pow(self.generator, b, self.prime)) % self.prime

        return beta, b

    def ot_send_response(
        self, beta: int, x0: int, x1: int, a: int, m0: int, m1: int
    ) -> Tuple[int, int]:
        """Sender creates response messages."""
        # Compute keys
        k0 = pow(beta, a, self.prime)
        k1 = pow((beta * pow(self.generator, -a, self.prime)) % self.prime, a, self.prime)

        # Encrypt messages
        c0 = (m0 + k0) % self.prime
        c1 = (m1 + k1) % self.prime

        return c0, c1

    def ot_receive_decrypt(self, c0: int, c1: int, choice_bit: int, alpha: int, b: int) -> int:
        """Receiver decrypts the chosen message."""
        if choice_bit == 0:
            k = pow(alpha, b, self.prime)
            return (c0 - k) % self.prime
        else:
            k = pow(alpha, b, self.prime)
            return (c1 - k) % self.prime
