"""
Modular arithmetic operations for homomorphic encryption.
"""

import logging
import math
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class ModularArithmetic:
    """
    Efficient modular arithmetic operations for large integers.

    Provides optimized implementations of modular operations used
    in homomorphic encryption schemes.
    """

    def __init__(self, moduli: List[int]):
        """
        Initialize modular arithmetic with given moduli.

        Args:
            moduli: List of moduli for Chinese Remainder Theorem
        """
        self.moduli = moduli
        self.num_moduli = len(moduli)

        # Precompute CRT parameters
        self.total_modulus = 1
        for m in moduli:
            self.total_modulus *= m

        self.crt_coefficients = self._compute_crt_coefficients()

        logger.debug(f"Initialized modular arithmetic with {len(moduli)} moduli")

    def _compute_crt_coefficients(self) -> List[Tuple[int, int]]:
        """
        Precompute Chinese Remainder Theorem coefficients.

        Returns:
            List of (Mi, yi) pairs for CRT reconstruction
        """
        coefficients = []

        for i, mi in enumerate(self.moduli):
            # Mi = M / mi
            Mi = self.total_modulus // mi

            # yi = Mi^(-1) mod mi
            yi = self.mod_inverse(Mi, mi)

            coefficients.append((Mi, yi))

        return coefficients

    def mod_add(self, a: int, b: int, modulus: int) -> int:
        """
        Modular addition: (a + b) mod m.

        Args:
            a: First operand
            b: Second operand
            modulus: Modulus

        Returns:
            (a + b) mod modulus
        """
        return (a + b) % modulus

    def mod_sub(self, a: int, b: int, modulus: int) -> int:
        """
        Modular subtraction: (a - b) mod m.

        Args:
            a: First operand
            b: Second operand
            modulus: Modulus

        Returns:
            (a - b) mod modulus
        """
        return (a - b) % modulus

    def mod_mul(self, a: int, b: int, modulus: int) -> int:
        """
        Modular multiplication: (a * b) mod m.

        Args:
            a: First operand
            b: Second operand
            modulus: Modulus

        Returns:
            (a * b) mod modulus
        """
        return (a * b) % modulus

    def mod_pow(self, base: int, exponent: int, modulus: int) -> int:
        """
        Modular exponentiation: base^exponent mod modulus.

        Uses fast exponentiation algorithm.

        Args:
            base: Base
            exponent: Exponent
            modulus: Modulus

        Returns:
            base^exponent mod modulus
        """
        return pow(base, exponent, modulus)

    def mod_inverse(self, a: int, modulus: int) -> int:
        """
        Modular multiplicative inverse: a^(-1) mod m.

        Uses extended Euclidean algorithm.

        Args:
            a: Number to find inverse of
            modulus: Modulus

        Returns:
            Modular inverse of a modulo modulus

        Raises:
            ValueError: If inverse doesn't exist (gcd(a, m) != 1)
        """
        if math.gcd(a, modulus) != 1:
            raise ValueError(f"Modular inverse of {a} mod {modulus} doesn't exist")

        # Extended Euclidean Algorithm
        def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
            if a == 0:
                return b, 0, 1

            gcd, x1, y1 = extended_gcd(b % a, a)
            x = y1 - (b // a) * x1
            y = x1

            return gcd, x, y

        gcd, x, _ = extended_gcd(a % modulus, modulus)
        return (x % modulus + modulus) % modulus

    def barrett_reduction(self, x: int, modulus: int, mu: Optional[int] = None) -> int:
        """
        Barrett reduction for efficient modular arithmetic.

        Args:
            x: Number to reduce
            modulus: Modulus
            mu: Precomputed Barrett parameter (computed if None)

        Returns:
            x mod modulus
        """
        if mu is None:
            # Compute Barrett parameter: mu = floor(2^(2k) / modulus)
            k = modulus.bit_length()
            mu = (1 << (2 * k)) // modulus

        # Barrett reduction algorithm
        k = modulus.bit_length()
        q = (x * mu) >> (2 * k)
        r = x - q * modulus

        while r >= modulus:
            r -= modulus

        return r

    def montgomery_reduction(
        self, x: int, modulus: int, r: Optional[int] = None, r_inv: Optional[int] = None
    ) -> int:
        """
        Montgomery reduction for efficient modular arithmetic.

        Args:
            x: Number to reduce (in Montgomery form)
            modulus: Modulus (must be odd)
            r: Montgomery radix (computed if None)
            r_inv: Modular inverse of r (computed if None)

        Returns:
            x * r^(-1) mod modulus
        """
        if modulus % 2 == 0:
            raise ValueError("Montgomery reduction requires odd modulus")

        if r is None:
            # Choose r = 2^k where k >= log2(modulus)
            k = modulus.bit_length()
            r = 1 << k

        if r_inv is None:
            r_inv = self.mod_inverse(r, modulus)

        # Montgomery reduction algorithm
        m = (-self.mod_inverse(modulus, r)) % r
        t = x + ((x * m) % r) * modulus
        t = t >> r.bit_length()

        if t >= modulus:
            t -= modulus

        return t

    def crt_reconstruct(self, remainders: List[int]) -> int:
        """
        Reconstruct integer from remainders using Chinese Remainder Theorem.

        Args:
            remainders: List of remainders for each modulus

        Returns:
            Reconstructed integer
        """
        if len(remainders) != self.num_moduli:
            raise ValueError("Number of remainders must match number of moduli")

        result = 0

        for i, (remainder, (Mi, yi)) in enumerate(zip(remainders, self.crt_coefficients)):
            # CRT formula: x = sum(ai * Mi * yi) mod M
            term = (remainder * Mi * yi) % self.total_modulus
            result = (result + term) % self.total_modulus

        return result

    def crt_decompose(self, x: int) -> List[int]:
        """
        Decompose integer into remainders using Chinese Remainder Theorem.

        Args:
            x: Integer to decompose

        Returns:
            List of remainders for each modulus
        """
        return [x % m for m in self.moduli]

    def karatsuba_multiply(self, x: int, y: int) -> int:
        """
        Karatsuba multiplication for large integers.

        Args:
            x: First operand
            y: Second operand

        Returns:
            Product x * y
        """
        # Base case for small numbers
        if x < 1000 or y < 1000:
            return x * y

        # Calculate size of numbers
        m = max(x.bit_length(), y.bit_length()) // 2

        # Split numbers
        high1, low1 = divmod(x, 1 << m)
        high2, low2 = divmod(y, 1 << m)

        # Recursive calls
        z0 = self.karatsuba_multiply(low1, low2)
        z1 = self.karatsuba_multiply(low1 + high1, low2 + high2)
        z2 = self.karatsuba_multiply(high1, high2)

        # Combine results
        return z2 * (1 << (2 * m)) + (z1 - z2 - z0) * (1 << m) + z0

    def gcd(self, a: int, b: int) -> int:
        """
        Greatest common divisor using Euclidean algorithm.

        Args:
            a: First number
            b: Second number

        Returns:
            GCD of a and b
        """
        while b:
            a, b = b, a % b
        return a

    def lcm(self, a: int, b: int) -> int:
        """
        Least common multiple.

        Args:
            a: First number
            b: Second number

        Returns:
            LCM of a and b
        """
        return abs(a * b) // self.gcd(a, b)

    def jacobi_symbol(self, a: int, n: int) -> int:
        """
        Compute Jacobi symbol (a/n).

        Args:
            a: Numerator
            n: Denominator (must be odd and positive)

        Returns:
            Jacobi symbol value (-1, 0, or 1)
        """
        if n <= 0 or n % 2 == 0:
            raise ValueError("n must be odd and positive")

        a = a % n
        result = 1

        while a != 0:
            while a % 2 == 0:
                a //= 2
                if n % 8 in [3, 5]:
                    result = -result

            a, n = n, a
            if a % 4 == 3 and n % 4 == 3:
                result = -result

            a = a % n

        return result if n == 1 else 0

    def is_quadratic_residue(self, a: int, p: int) -> bool:
        """
        Check if a is a quadratic residue modulo p.

        Args:
            a: Number to check
            p: Prime modulus

        Returns:
            True if a is a quadratic residue mod p
        """
        if p == 2:
            return True

        return self.jacobi_symbol(a, p) == 1

    def sqrt_mod(self, a: int, p: int) -> Optional[int]:
        """
        Compute square root modulo p using Tonelli-Shanks algorithm.

        Args:
            a: Number to find square root of
            p: Prime modulus

        Returns:
            Square root of a mod p, or None if doesn't exist
        """
        if not self.is_quadratic_residue(a, p):
            return None

        if p % 4 == 3:
            # Simple case: r = a^((p+1)/4) mod p
            return pow(a, (p + 1) // 4, p)

        # Tonelli-Shanks algorithm for p ≡ 1 (mod 4)
        # Find Q and S such that p-1 = Q * 2^S with Q odd
        Q = p - 1
        S = 0
        while Q % 2 == 0:
            Q //= 2
            S += 1

        # Find quadratic non-residue z
        z = 2
        while self.is_quadratic_residue(z, p):
            z += 1

        # Initialize variables
        M = S
        c = pow(z, Q, p)
        t = pow(a, Q, p)
        R = pow(a, (Q + 1) // 2, p)

        while t != 1:
            # Find smallest i such that t^(2^i) = 1
            i = 1
            temp = (t * t) % p
            while temp != 1:
                temp = (temp * temp) % p
                i += 1

            # Update variables
            b = pow(c, 1 << (M - i - 1), p)
            M = i
            c = (b * b) % p
            t = (t * c) % p
            R = (R * b) % p

        return R

    def legendre_symbol(self, a: int, p: int) -> int:
        """
        Compute Legendre symbol (a/p) for prime p.

        Args:
            a: Numerator
            p: Prime denominator

        Returns:
            Legendre symbol value (-1, 0, or 1)
        """
        return pow(a, (p - 1) // 2, p) % p

    def euler_totient(self, n: int) -> int:
        """
        Compute Euler's totient function φ(n).

        Args:
            n: Input number

        Returns:
            Number of integers ≤ n that are coprime to n
        """
        result = n
        p = 2

        while p * p <= n:
            if n % p == 0:
                while n % p == 0:
                    n //= p
                result -= result // p
            p += 1

        if n > 1:
            result -= result // n

        return result

    def primitive_root(self, p: int) -> Optional[int]:
        """
        Find a primitive root modulo prime p.

        Args:
            p: Prime modulus

        Returns:
            Primitive root modulo p, or None if p is not prime
        """
        if p <= 1:
            return None

        # Check if p is prime (simplified check)
        for i in range(2, int(p**0.5) + 1):
            if p % i == 0:
                return None

        phi = p - 1
        factors = []

        # Find prime factors of φ(p) = p-1
        temp = phi
        d = 2
        while d * d <= temp:
            if temp % d == 0:
                factors.append(d)
                while temp % d == 0:
                    temp //= d
            d += 1
        if temp > 1:
            factors.append(temp)

        # Test candidates
        for g in range(2, p):
            is_primitive = True
            for factor in factors:
                if pow(g, phi // factor, p) == 1:
                    is_primitive = False
                    break

            if is_primitive:
                return g

        return None
