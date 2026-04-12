"""
Zero-Knowledge Proof System for Kenny AGI Blockchain Audit Trail

Provides an abstract ZK proof interface and a concrete Schnorr protocol
implementation for non-interactive zero-knowledge proofs of knowledge.
"""

import hashlib
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)


@dataclass
class ZKProof:
    """Represents a zero-knowledge proof"""

    proof_type: str
    commitment: str  # hex-encoded commitment value
    challenge: str  # hex-encoded challenge value
    response: str  # hex-encoded response value
    public_input: Optional[str] = None  # hex-encoded public input
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "proof_type": self.proof_type,
            "commitment": self.commitment,
            "challenge": self.challenge,
            "response": self.response,
            "public_input": self.public_input,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZKProof":
        """Create from dictionary"""
        return cls(
            proof_type=data["proof_type"],
            commitment=data["commitment"],
            challenge=data["challenge"],
            response=data["response"],
            public_input=data.get("public_input"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class ZKProofSystem(ABC):
    """Abstract base class for zero-knowledge proof systems"""

    @abstractmethod
    def prove(self, witness: bytes, public_input: bytes = b"") -> ZKProof:
        """
        Generate a zero-knowledge proof

        Args:
            witness: Secret witness (e.g. private key bytes)
            public_input: Optional public input bound into the proof

        Returns:
            A ZKProof instance
        """
        ...

    @abstractmethod
    def verify(self, proof: ZKProof, public_input: bytes = b"") -> bool:
        """
        Verify a zero-knowledge proof

        Args:
            proof: The proof to verify
            public_input: Optional public input (must match what was used in prove)

        Returns:
            True if the proof is valid
        """
        ...


class SchnorrProofSystem(ZKProofSystem):
    """
    Schnorr NIZK proof of knowledge of discrete log

    Proves: "I know *x* such that *P* = *x* · *G*" without revealing *x*.
    Uses the Fiat-Shamir heuristic for non-interactivity.

    Protocol (NIZK via Fiat-Shamir):
        1. Prover picks random *k*, computes **R** = *k* · *G* (commitment)
        2. Prover computes *e* = H(**R** ‖ **P** ‖ public_input) (challenge)
        3. Prover computes *s* = (*k* − *e* · *x*) mod *n* (response)
        4. Verifier checks *s* · *G* + *e* · **P** == **R**

    Curve defaults to secp256k1 but any ``ec.EllipticCurve`` is accepted.
    """

    def __init__(self, curve: Optional[ec.EllipticCurve] = None):
        """
        Initialize the Schnorr proof system

        Args:
            curve: Elliptic curve to use (defaults to SECP256K1)
        """
        self._curve = curve or ec.SECP256K1()

    # ------------------------------------------------------------------
    # Curve constants
    # ------------------------------------------------------------------

    _ORDERS: Dict[str, int] = {
        "secp256k1": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141,
        "secp256r1": 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551,
        "secp384r1": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC7634D81F4372DDF581A0DB248B0A77AECEC196ACCC52973,
        "secp521r1": 0x01FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFA51868783BF2F966B7FCC0148F709A5D03BB5C9B8899C47AEBB6FB71E91386409,
    }

    _PRIMES: Dict[str, int] = {
        "secp256k1": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F,
        "secp256r1": 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF,
        "secp384r1": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFF0000000000000000FFFFFFFF,
        "secp521r1": 0x01FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
    }

    _A_COEFFICIENTS: Dict[str, int] = {
        "secp256k1": 0,
        "secp256r1": 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC,
        "secp384r1": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFF0000000000000000FFFFFFFC,
        "secp521r1": 0x01FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC,
    }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _order(self) -> int:
        """Return the group order *n* for the configured curve"""
        name = self._curve.name
        if name in self._ORDERS:
            return self._ORDERS[name]
        raise ValueError(f"Unknown curve order for: {name}")

    def _field_prime(self) -> int:
        """Return the field prime *p* for the configured curve"""
        name = self._curve.name
        if name in self._PRIMES:
            return self._PRIMES[name]
        raise ValueError(f"Unknown field prime for: {name}")

    def _curve_a(self) -> int:
        """Return the 'a' coefficient of y² = x³ + ax + b"""
        name = self._curve.name
        if name in self._A_COEFFICIENTS:
            return self._A_COEFFICIENTS[name]
        raise ValueError(f"Unknown 'a' coefficient for: {name}")

    @staticmethod
    def _encode_point(pub: ec.EllipticCurvePublicKey) -> bytes:
        """Serialize a public key to uncompressed point bytes (0x04 ‖ x ‖ y)"""
        return pub.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )

    def _scalar_mult_G(self, scalar: int) -> ec.EllipticCurvePublicKey:
        """Compute *scalar* · *G* by constructing a private key"""
        n = self._order()
        scalar = scalar % n
        if scalar == 0:
            raise ValueError("Scalar must be non-zero")
        priv = ec.derive_private_key(scalar, self._curve)
        return priv.public_key()

    @staticmethod
    def _affine_add(
        x1: int, y1: int, x2: int, y2: int, p: int, a: int
    ) -> Tuple[int, int]:
        """Affine point addition / doubling on short-Weierstrass curve"""
        if x1 == x2 and y1 == y2:
            # Point doubling
            lam = ((3 * x1 * x1 + a) * pow(2 * y1, -1, p)) % p
        elif x1 == x2:
            raise ValueError("Points are inverses; sum is point at infinity")
        else:
            lam = ((y2 - y1) * pow(x2 - x1, -1, p)) % p

        x3 = (lam * lam - x1 - x2) % p
        y3 = (lam * (x1 - x3) - y1) % p
        return x3, y3

    def _scalar_mult_point(
        self, scalar: int, px: int, py: int
    ) -> ec.EllipticCurvePublicKey:
        """
        Compute *scalar* · (*px*, *py*) using double-and-add.
        Returns the result as an EC public key object.
        """
        n = self._order()
        p = self._field_prime()
        a = self._curve_a()
        scalar = scalar % n

        if scalar == 0:
            raise ValueError("Scalar must be non-zero for point multiplication")

        # Double-and-add in affine coordinates
        rx, ry = None, None  # point at infinity
        qx, qy = px, py

        while scalar > 0:
            if scalar & 1:
                if rx is None:
                    rx, ry = qx, qy
                else:
                    rx, ry = self._affine_add(rx, ry, qx, qy, p, a)
            qx, qy = self._affine_add(qx, qy, qx, qy, p, a)
            scalar >>= 1

        result_numbers = ec.EllipticCurvePublicNumbers(
            x=rx, y=ry, curve=self._curve
        )
        return result_numbers.public_key()

    def _point_add(
        self,
        p1: ec.EllipticCurvePublicKey,
        p2: ec.EllipticCurvePublicKey,
    ) -> ec.EllipticCurvePublicKey:
        """Add two EC points via explicit affine addition"""
        nums1 = p1.public_numbers()
        nums2 = p2.public_numbers()
        p = self._field_prime()
        a = self._curve_a()

        x3, y3 = self._affine_add(
            nums1.x, nums1.y, nums2.x, nums2.y, p, a
        )

        result_numbers = ec.EllipticCurvePublicNumbers(
            x=x3, y=y3, curve=self._curve
        )
        return result_numbers.public_key()

    # ------------------------------------------------------------------
    # Key-pair generation convenience
    # ------------------------------------------------------------------

    def generate_key_pair(
        self,
    ) -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """
        Generate a new EC key pair on the configured curve

        Returns:
            Tuple of (private_key, public_key)
        """
        private_key = ec.generate_private_key(self._curve)
        return private_key, private_key.public_key()

    # ------------------------------------------------------------------
    # Prove / Verify
    # ------------------------------------------------------------------

    def prove(self, witness: bytes, public_input: bytes = b"") -> ZKProof:
        """
        Generate a Schnorr NIZK proof

        The *witness* is interpreted as a big-endian unsigned integer
        representing the discrete-log secret *x*.  The public statement
        **P** = *x* · *G* is computed internally.

        Args:
            witness: Secret scalar as bytes (big-endian)
            public_input: Optional context bytes bound into the challenge

        Returns:
            A ZKProof with commitment R, challenge e, response s
        """
        n = self._order()

        # Interpret witness as secret scalar x
        x = int.from_bytes(witness, "big") % n
        if x == 0:
            raise ValueError("Witness must be non-zero")

        # Public key P = x * G
        P = self._scalar_mult_G(x)
        P_bytes = self._encode_point(P)

        # Step 1: random nonce k, commitment R = k * G
        k = int.from_bytes(os.urandom(32), "big") % n
        if k == 0:
            k = 1  # extremely unlikely, but be safe
        R = self._scalar_mult_G(k)
        R_bytes = self._encode_point(R)

        # Step 2: Fiat-Shamir challenge e = H(R || P || public_input)
        h = hashlib.sha256()
        h.update(R_bytes)
        h.update(P_bytes)
        h.update(public_input)
        e = int.from_bytes(h.digest(), "big") % n

        # Step 3: response s = (k - e * x) mod n
        s = (k - e * x) % n

        proof = ZKProof(
            proof_type="schnorr",
            commitment=R_bytes.hex(),
            challenge=e.to_bytes(32, "big").hex(),
            response=s.to_bytes(32, "big").hex(),
            public_input=P_bytes.hex(),  # verifier needs P
            timestamp=datetime.now(),
            metadata={"curve": self._curve.name},
        )

        logger.info("Generated Schnorr NIZK proof")
        return proof

    def verify(self, proof: ZKProof, public_input: bytes = b"") -> bool:
        """
        Verify a Schnorr NIZK proof

        Checks that *s* · *G* + *e* · *P* == *R*.

        Args:
            proof: The ZKProof to verify
            public_input: Context bytes (must match what prover used)

        Returns:
            True if the proof is valid
        """
        if proof.proof_type != "schnorr":
            logger.warning(f"Unsupported proof type: {proof.proof_type}")
            return False

        try:
            n = self._order()

            R_bytes = bytes.fromhex(proof.commitment)
            s = int.from_bytes(bytes.fromhex(proof.response), "big")
            P_bytes = bytes.fromhex(proof.public_input)

            # Reconstruct P from its uncompressed encoding
            P = ec.EllipticCurvePublicKey.from_encoded_point(self._curve, P_bytes)
            P_nums = P.public_numbers()

            # Recompute challenge e = H(R || P || public_input)
            h = hashlib.sha256()
            h.update(R_bytes)
            h.update(P_bytes)
            h.update(public_input)
            e = int.from_bytes(h.digest(), "big") % n

            # Verify: s*G + e*P == R
            # Compute e*P using explicit point multiplication
            eP = self._scalar_mult_point(e, P_nums.x, P_nums.y)

            if s == 0:
                # R should equal e*P
                R_check = eP
            else:
                sG = self._scalar_mult_G(s)
                R_check = self._point_add(sG, eP)

            R_check_bytes = self._encode_point(R_check)

            valid = R_check_bytes == R_bytes
            if valid:
                logger.info("Schnorr proof verified successfully")
            else:
                logger.warning("Schnorr proof verification failed")
            return valid

        except Exception as e:
            logger.warning(f"Schnorr proof verification error: {str(e)}")
            return False
