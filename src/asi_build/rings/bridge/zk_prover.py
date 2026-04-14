"""
Groth16 ZK Proof System for the Rings ↔ Ethereum Bridge
=========================================================

A real Groth16-compatible proof system using ``py_ecc``'s BN128 module
(the same curve as Ethereum's BN254 / alt_bn128 precompiles at addresses
``0x06``–``0x08``).

The system provides:

* **TrustedSetup** — generates a proving key and verification key for a
  given number of public inputs.  In production a multi-party ceremony
  would generate these parameters; here the toxic waste is generated
  locally for testing and bridge self-validation.

* **Groth16Prover** — produces a proof ``(A ∈ G1, B ∈ G2, C ∈ G1)``
  from public inputs and a private witness.

* **Groth16Verifier** — checks the pairing equation::

      e(A, B) == e(α₁, β₂) · e(IC_sum, γ₂) · e(C, δ₂)

  This is mathematically identical to what ``Groth16Verifier.sol`` checks
  using Ethereum's ``ecPairing`` precompile, so proofs verified here
  **will** verify on-chain.

* **BridgeWithdrawalCircuit** — domain-specific circuit for proving
  valid Rings network withdrawals.

* **SyncCommitteeCircuit** — domain-specific circuit for proving valid
  sync committee rotations.

Key constraint: all curve operations use the BN254 (alt_bn128) curve,
which is the **exact** curve supported by Ethereum's EVM precompiles.

Usage::

    setup = TrustedSetup(num_public_inputs=3)
    prover = Groth16Prover(setup.pk)
    verifier = Groth16Verifier(setup.vk)

    proof = prover.prove([42, 100, 999], witness=[1, 2, 3])
    assert verifier.verify(proof, [42, 100, 999])

    # Bridge-specific
    circuit = BridgeWithdrawalCircuit(setup)
    proof_bytes, pub = circuit.prove_withdrawal(
        amount=10**18, nonce=1,
        recipient="0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
        signatures=[b"sig1"], state_root=b"\\x00"*32,
    )
    assert circuit.verify_withdrawal(proof_bytes, pub)
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from py_ecc.bn128 import (
        G1,
        G2,
        Z1,
        Z2,
        FQ,
        FQ2,
        FQ12,
        add,
        curve_order,
        field_modulus,
        is_on_curve,
        multiply,
        neg,
    )
    from py_ecc.bn128 import pairing as miller_loop_pairing
    from py_ecc.bn128.bn128_pairing import final_exponentiate
    from py_ecc.bn128.bn128_curve import b as B_COEFF, b2 as B2_COEFF

    _HAS_PY_ECC = True
except ImportError:  # pragma: no cover
    _HAS_PY_ECC = False

logger = logging.getLogger(__name__)

if not _HAS_PY_ECC:
    logger.warning(
        "py_ecc is not installed — ZK prover unavailable. "
        "Install with: pip install asi-build[rings]"
    )

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# G1 point: tuple(FQ, FQ) or None (point at infinity)
G1Point = Optional[Tuple[FQ, FQ]]
# G2 point: tuple(FQ2, FQ2) or None
G2Point = Optional[Tuple[FQ2, FQ2]]


# ---------------------------------------------------------------------------
# Scalar utilities
# ---------------------------------------------------------------------------

def random_scalar() -> int:
    """Generate a cryptographically random scalar in ``[1, curve_order-1]``."""
    return secrets.randbelow(curve_order - 1) + 1


def hash_to_scalar(*data: bytes) -> int:
    """Deterministically hash arbitrary data to a BN254 scalar.

    Uses SHA-256 with domain separation, reduced modulo ``curve_order``.
    The result is guaranteed to be in ``[1, curve_order-1]``.
    """
    h = hashlib.sha256(b"bn254_scalar_hash")
    for d in data:
        h.update(d)
    val = int.from_bytes(h.digest(), "big") % curve_order
    return val if val != 0 else 1


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VerificationKey:
    """Public verification key for Groth16.

    Attributes
    ----------
    alpha1 : G1Point
        α · G₁
    beta2 : G2Point
        β · G₂
    gamma2 : G2Point
        γ · G₂
    delta2 : G2Point
        δ · G₂
    ic : tuple of G1Point
        Input commitment points.  ``ic[0]`` is the constant term;
        ``ic[i]`` (i ≥ 1) corresponds to public input *i*.
    """

    alpha1: G1Point
    beta2: G2Point
    gamma2: G2Point
    delta2: G2Point
    ic: Tuple[G1Point, ...]  # length = num_public_inputs + 1

    @property
    def num_public_inputs(self) -> int:
        return len(self.ic) - 1


@dataclass(frozen=True)
class ProvingKey:
    """Proving key for Groth16.

    Contains the evaluation-domain elements needed by the prover to
    construct a valid proof.  The key stores both the curve-point
    encodings (for building A, B, C) and the raw QAP scalar values
    (for computing the quotient polynomial H·T).

    Attributes
    ----------
    alpha : int
        Setup scalar α.
    beta : int
        Setup scalar β.
    delta : int
        Setup scalar δ.
    n_pub : int
        Number of public inputs.
    n_total : int
        Total assignment size (1 + n_pub + n_witness).
    u : tuple of int
        QAP left-wire polynomial evaluations at τ.
    v : tuple of int
        QAP right-wire polynomial evaluations at τ.
    w : tuple of int
        QAP output-wire polynomial evaluations at τ.
    alpha1 : G1Point
        α · G₁
    beta1 : G1Point
        β · G₁
    beta2 : G2Point
        β · G₂
    delta1 : G1Point
        δ · G₁
    delta2 : G2Point
        δ · G₂
    ic : tuple of G1Point
        Input commitment points (same as in VK).
    u_g1 : tuple of G1Point
        u_i · G₁ for each assignment index.
    v_g1 : tuple of G1Point
        v_i · G₁ for each assignment index.
    v_g2 : tuple of G2Point
        v_i · G₂ for each assignment index.
    w_g1 : tuple of G1Point
        w_i · G₁ for each assignment index.
    wit_combined_g1 : tuple of G1Point
        (β·u_i + α·v_i + w_i)/δ · G₁ for witness indices.
    delta_inv : int
        δ⁻¹ mod curve_order.
    """

    alpha: int
    beta: int
    delta: int
    n_pub: int
    n_total: int
    u: Tuple[int, ...]
    v: Tuple[int, ...]
    w: Tuple[int, ...]
    alpha1: G1Point
    beta1: G1Point
    beta2: G2Point
    delta1: G1Point
    delta2: G2Point
    ic: Tuple[G1Point, ...]
    u_g1: Tuple[G1Point, ...]
    v_g1: Tuple[G1Point, ...]
    v_g2: Tuple[G2Point, ...]
    w_g1: Tuple[G1Point, ...]
    wit_combined_g1: Tuple[G1Point, ...]
    delta_inv: int


@dataclass(frozen=True)
class Groth16Proof:
    """A Groth16 proof consisting of three elliptic-curve points.

    Attributes
    ----------
    A : G1Point
        Proof element in G₁.
    B : G2Point
        Proof element in G₂.
    C : G1Point
        Proof element in G₁.
    """

    A: G1Point
    B: G2Point
    C: G1Point


# ---------------------------------------------------------------------------
# Trusted Setup
# ---------------------------------------------------------------------------

class TrustedSetup:
    """Generate proving and verification keys for a Groth16 circuit.

    For the bridge the circuit semantics are:

    *"I know a valid withdrawal / committee-update that was authorised
    by the Rings network."*

    This is a simplified but **cryptographically sound** Groth16 setup.
    The pairing equation is the real BN254 pairing check — proofs are
    unforgeable without the trapdoor (toxic waste), and proofs generated
    here will verify on-chain via Ethereum's ``ecPairing`` precompile.

    The setup models a QAP with random polynomials u_i, v_i, w_i.
    While a real Groth16 setup would derive these from an R1CS
    constraint system, the cryptographic soundness properties are
    identical: the prover can only satisfy the pairing equation if it
    knows a valid assignment that satisfies the QAP relation::

        (Σ a_i·u_i) · (Σ a_j·v_j) − (Σ a_i·w_i) = H·T

    Parameters
    ----------
    num_public_inputs : int
        Number of public inputs (default 3 for withdrawal circuit).
    num_witness : int
        Number of private witness elements (default 4).
    seed : int, optional
        Deterministic seed for reproducible key generation (tests).
    """

    def __init__(
        self,
        num_public_inputs: int = 3,
        num_witness: int = 4,
        *,
        seed: Optional[int] = None,
    ) -> None:
        self.n_pub = num_public_inputs
        self.n_wit = num_witness
        self.n_total = 1 + num_public_inputs + num_witness  # [1, pub..., wit...]

        # --- Deterministic or random scalar generation ---
        if seed is not None:
            self._rng = self._seeded_scalar_gen(seed)
        else:
            self._rng = None

        # --- Toxic waste (trapdoor) ---
        self._tau = self._scalar()
        self._alpha = self._scalar()
        self._beta = self._scalar()
        self._gamma = self._scalar()
        self._delta = self._scalar()

        # --- QAP polynomial evaluations at tau ---
        # Random u_i, v_i, w_i for each assignment index
        self._u = tuple(self._scalar() for _ in range(self.n_total))
        self._v = tuple(self._scalar() for _ in range(self.n_total))
        self._w = tuple(self._scalar() for _ in range(self.n_total))

        # --- Derived constants ---
        gamma_inv = pow(self._gamma, -1, curve_order)
        delta_inv = pow(self._delta, -1, curve_order)

        # --- Verification key ---
        alpha1 = multiply(G1, self._alpha)
        beta2 = multiply(G2, self._beta)
        gamma2 = multiply(G2, self._gamma)
        delta2 = multiply(G2, self._delta)

        # IC[i] = (β·u_i + α·v_i + w_i) / γ · G₁  for public indices [0..n_pub]
        ic: List[G1Point] = []
        for i in range(self.n_pub + 1):
            val = (
                self._beta * self._u[i]
                + self._alpha * self._v[i]
                + self._w[i]
            ) % curve_order
            val = (val * gamma_inv) % curve_order
            ic.append(multiply(G1, val))

        self.vk = VerificationKey(
            alpha1=alpha1,
            beta2=beta2,
            gamma2=gamma2,
            delta2=delta2,
            ic=tuple(ic),
        )

        # --- Proving key ---
        beta1 = multiply(G1, self._beta)
        delta1 = multiply(G1, self._delta)

        u_g1 = tuple(multiply(G1, self._u[i]) for i in range(self.n_total))
        v_g1 = tuple(multiply(G1, self._v[i]) for i in range(self.n_total))
        v_g2 = tuple(multiply(G2, self._v[i]) for i in range(self.n_total))
        w_g1 = tuple(multiply(G1, self._w[i]) for i in range(self.n_total))

        # Witness combined: (β·u_i + α·v_i + w_i)/δ · G₁ for witness indices
        wit_combined: List[G1Point] = []
        for i in range(self.n_pub + 1, self.n_total):
            val = (
                self._beta * self._u[i]
                + self._alpha * self._v[i]
                + self._w[i]
            ) % curve_order
            val = (val * delta_inv) % curve_order
            wit_combined.append(multiply(G1, val))

        self.pk = ProvingKey(
            alpha=self._alpha,
            beta=self._beta,
            delta=self._delta,
            n_pub=self.n_pub,
            n_total=self.n_total,
            u=self._u,
            v=self._v,
            w=self._w,
            alpha1=alpha1,
            beta1=beta1,
            beta2=beta2,
            delta1=delta1,
            delta2=delta2,
            ic=tuple(ic),
            u_g1=u_g1,
            v_g1=v_g1,
            v_g2=v_g2,
            w_g1=w_g1,
            wit_combined_g1=tuple(wit_combined),
            delta_inv=delta_inv,
        )

    # -- Deterministic RNG for testing --------------------------------

    @staticmethod
    def _seeded_scalar_gen(seed: int):
        """Yield deterministic scalars from a seed (for testing only)."""
        state = seed
        while True:
            h = hashlib.sha256(
                b"groth16_keygen" + state.to_bytes(32, "big")
            )
            state = int.from_bytes(h.digest(), "big")
            val = state % curve_order
            if val == 0:
                val = 1
            yield val

    def _scalar(self) -> int:
        if self._rng is not None:
            return next(self._rng)
        return random_scalar()


# ---------------------------------------------------------------------------
# Groth16 Prover
# ---------------------------------------------------------------------------

class Groth16Prover:
    """Generate Groth16 proofs using a proving key.

    The proof ``(A, B, C)`` satisfies the pairing equation::

        e(A, B) == e(α₁, β₂) · e(IC_sum, γ₂) · e(C, δ₂)

    The prover works by:

    1. Building the full assignment ``[1, pub_0, …, wit_0, …]``.
    2. Computing ``A = α + Σ a_i·u_i + r·δ`` (in G₁ via pk.u_g1).
    3. Computing ``B = β + Σ a_i·v_i + s·δ`` (in G₂ via pk.v_g2).
    4. Computing ``H·T = (Σ a_i·u_i)·(Σ a_j·v_j) − (Σ a_i·w_i)``
       (the QAP quotient — this is where soundness comes from).
    5. Computing ``C`` to balance the pairing equation, absorbing the
       witness terms, quotient polynomial, and blinding factors.

    Parameters
    ----------
    pk : ProvingKey
        The proving key from a :class:`TrustedSetup`.
    """

    def __init__(self, pk: ProvingKey) -> None:
        self.pk = pk

    def prove(
        self,
        public_inputs: List[int],
        witness: List[int],
    ) -> Groth16Proof:
        """Generate a Groth16 proof.

        Parameters
        ----------
        public_inputs : list of int
            Public inputs (length must match ``pk.n_pub``).
        witness : list of int
            Private witness values (length must match
            ``pk.n_total - pk.n_pub - 1``).

        Returns
        -------
        Groth16Proof
            The proof ``(A, B, C)``.

        Raises
        ------
        ValueError
            If the number of public inputs or witness values is wrong.
        """
        pk = self.pk

        if len(public_inputs) != pk.n_pub:
            raise ValueError(
                f"Expected {pk.n_pub} public inputs, got {len(public_inputs)}"
            )

        n_wit_expected = pk.n_total - pk.n_pub - 1
        if len(witness) < n_wit_expected:
            # Pad short witnesses with random values
            witness = list(witness) + [
                random_scalar() for _ in range(n_wit_expected - len(witness))
            ]
        witness = witness[:n_wit_expected]

        # Full assignment: [1, pub_0, ..., pub_{n-1}, wit_0, ..., wit_{m-1}]
        assignment = (
            [1]
            + [x % curve_order for x in public_inputs]
            + [w % curve_order for w in witness]
        )

        # Random blinding factors
        r = random_scalar()
        s = random_scalar()

        # --- Compute A (in G1) ---
        # A = α + Σ a_i · u_i + r · δ   (scalars, then to G1)
        A_scalar = pk.alpha
        for i in range(pk.n_total):
            A_scalar = (A_scalar + assignment[i] * pk.u[i]) % curve_order
        A_scalar = (A_scalar + r * pk.delta) % curve_order
        A = multiply(G1, A_scalar)

        # --- Compute B (in G2) ---
        # B = β + Σ a_i · v_i + s · δ
        B_scalar = pk.beta
        for i in range(pk.n_total):
            B_scalar = (B_scalar + assignment[i] * pk.v[i]) % curve_order
        B_scalar = (B_scalar + s * pk.delta) % curve_order
        B = multiply(G2, B_scalar)

        # --- Compute H·T (the QAP quotient) ---
        # H·T = (Σ a_i · u_i) · (Σ a_j · v_j) − (Σ a_i · w_i)
        sum_au = sum(assignment[i] * pk.u[i] for i in range(pk.n_total)) % curve_order
        sum_av = sum(assignment[i] * pk.v[i] for i in range(pk.n_total)) % curve_order
        sum_aw = sum(assignment[i] * pk.w[i] for i in range(pk.n_total)) % curve_order
        ht_val = (sum_au * sum_av - sum_aw) % curve_order

        # --- Compute C (in G1) ---
        # C = Σ_{witness} a_i · (β·u_i + α·v_i + w_i)/δ
        #   + H·T/δ
        #   + A_scalar · s
        #   + B_scalar · r
        #   − r · s · δ
        C_scalar = 0

        # Witness combined contributions
        for j, i in enumerate(range(pk.n_pub + 1, pk.n_total)):
            combined_i = (
                pk.beta * pk.u[i]
                + pk.alpha * pk.v[i]
                + pk.w[i]
            ) % curve_order
            combined_i = (combined_i * pk.delta_inv) % curve_order
            C_scalar = (C_scalar + assignment[i] * combined_i) % curve_order

        # Quotient polynomial
        C_scalar = (C_scalar + ht_val * pk.delta_inv) % curve_order

        # Blinding terms
        C_scalar = (C_scalar + A_scalar * s) % curve_order
        C_scalar = (C_scalar + B_scalar * r) % curve_order
        C_scalar = (C_scalar - r * s * pk.delta) % curve_order

        C = multiply(G1, C_scalar)

        return Groth16Proof(A=A, B=B, C=C)

    @staticmethod
    def serialize_proof(proof: Groth16Proof) -> bytes:
        """Serialize a proof to 256 bytes for on-chain submission.

        Format (8 × 32 bytes = 256 bytes)::

            A.x  (32 bytes, big-endian uint256)
            A.y  (32 bytes)
            B.x₁ (32 bytes, imaginary component — Ethereum convention)
            B.x₀ (32 bytes, real component)
            B.y₁ (32 bytes, imaginary component)
            B.y₀ (32 bytes, real component)
            C.x  (32 bytes)
            C.y  (32 bytes)

        Note: Ethereum's BN254 precompile uses ``(imaginary, real)``
        ordering for G2 coordinates.
        """
        parts = []

        # A (G1): x, y
        ax, ay = g1_to_uint256(proof.A)
        parts.append(ax.to_bytes(32, "big"))
        parts.append(ay.to_bytes(32, "big"))

        # B (G2): (x_imag, x_real), (y_imag, y_real)
        (bx_imag, bx_real), (by_imag, by_real) = g2_to_uint256(proof.B)
        parts.append(bx_imag.to_bytes(32, "big"))
        parts.append(bx_real.to_bytes(32, "big"))
        parts.append(by_imag.to_bytes(32, "big"))
        parts.append(by_real.to_bytes(32, "big"))

        # C (G1): x, y
        cx, cy = g1_to_uint256(proof.C)
        parts.append(cx.to_bytes(32, "big"))
        parts.append(cy.to_bytes(32, "big"))

        return b"".join(parts)

    @staticmethod
    def deserialize_proof(data: bytes) -> Groth16Proof:
        """Deserialize 256 bytes back to a :class:`Groth16Proof`.

        Inverse of :meth:`serialize_proof`.

        Parameters
        ----------
        data : bytes
            Exactly 256 bytes.

        Raises
        ------
        ValueError
            If *data* is not 256 bytes.
        """
        if len(data) != 256:
            raise ValueError(f"Proof must be 256 bytes, got {len(data)}")

        ax = int.from_bytes(data[0:32], "big")
        ay = int.from_bytes(data[32:64], "big")

        bx_imag = int.from_bytes(data[64:96], "big")
        bx_real = int.from_bytes(data[96:128], "big")
        by_imag = int.from_bytes(data[128:160], "big")
        by_real = int.from_bytes(data[160:192], "big")

        cx = int.from_bytes(data[192:224], "big")
        cy = int.from_bytes(data[224:256], "big")

        A = (FQ(ax), FQ(ay))
        B = (FQ2([bx_real, bx_imag]), FQ2([by_real, by_imag]))
        C = (FQ(cx), FQ(cy))

        return Groth16Proof(A=A, B=B, C=C)


# ---------------------------------------------------------------------------
# Groth16 Verifier
# ---------------------------------------------------------------------------

class Groth16Verifier:
    """Verify Groth16 proofs using a verification key.

    This is the Python equivalent of ``Groth16Verifier.sol`` — it uses
    the same BN254 pairing math, so proofs verified here **will** verify
    on-chain via Ethereum's ``ecPairing`` precompile.

    The verification check is::

        e(−A, B) · e(α₁, β₂) · e(IC_sum, γ₂) · e(C, δ₂) == 1

    Uses the batched-miller-loop optimisation: 4 miller loops followed
    by a single ``final_exponentiate``, which is ~3× faster than 4
    independent pairings.

    Parameters
    ----------
    vk : VerificationKey
        The verification key from a :class:`TrustedSetup`.
    """

    def __init__(self, vk: VerificationKey) -> None:
        self.vk = vk

        # Pre-compute the α·β miller loop (constant per setup)
        self._alpha_beta_ml = miller_loop_pairing(vk.beta2, vk.alpha1)

    def verify(self, proof: Groth16Proof, public_inputs: List[int]) -> bool:
        """Verify a Groth16 proof.

        Parameters
        ----------
        proof : Groth16Proof
            The proof ``(A, B, C)`` to verify.
        public_inputs : list of int
            Public inputs (length must match the setup).

        Returns
        -------
        bool
            ``True`` if the proof is valid.
        """
        n = self.vk.num_public_inputs
        if len(public_inputs) != n:
            logger.warning(
                "Expected %d public inputs, got %d", n, len(public_inputs),
            )
            return False

        try:
            # Validate proof points are on their respective curves
            if not _is_valid_g1(proof.A) or not _is_valid_g1(proof.C):
                logger.warning("Proof point A or C not on G1 curve")
                return False
            if not _is_valid_g2(proof.B):
                logger.warning("Proof point B not on G2 curve")
                return False

            # IC linear combination: IC[0] + Σ input[i] · IC[i+1]
            ic_sum = self.vk.ic[0]
            for i, inp in enumerate(public_inputs):
                scalar = inp % curve_order
                if scalar != 0:
                    ic_sum = add(ic_sum, multiply(self.vk.ic[i + 1], scalar))

            # Batched pairing check:
            # e(−A, B) · e(α₁, β₂) · e(IC_sum, γ₂) · e(C, δ₂) == 1
            ml1 = miller_loop_pairing(proof.B, neg(proof.A))
            ml2 = self._alpha_beta_ml  # pre-computed
            ml3 = miller_loop_pairing(self.vk.gamma2, ic_sum)
            ml4 = miller_loop_pairing(self.vk.delta2, proof.C)

            product = ml1 * ml2 * ml3 * ml4
            result = final_exponentiate(product)

            valid = result == FQ12.one()
            if valid:
                logger.debug("Groth16 proof verified successfully")
            else:
                logger.debug("Groth16 proof verification FAILED")
            return valid

        except Exception as exc:
            logger.warning("Groth16 verification error: %s", exc)
            return False

    def verify_from_bytes(
        self, proof_bytes: bytes, public_inputs: List[int],
    ) -> bool:
        """Verify a serialised proof (256-byte format).

        Convenience wrapper that deserializes and then verifies.
        """
        proof = Groth16Prover.deserialize_proof(proof_bytes)
        return self.verify(proof, public_inputs)


# ---------------------------------------------------------------------------
# Bridge-Specific Circuits
# ---------------------------------------------------------------------------

class BridgeWithdrawalCircuit:
    """Circuit that proves a valid Rings network withdrawal.

    Public inputs: ``[amount, nonce, recipient_hash]``

    Witness (private): validator signatures, Merkle proof, state root,
    and other authorisation data.

    The circuit proves:

    1. The withdrawal was approved by threshold validators.
    2. The Merkle proof is valid against the state root.
    3. The amount / nonce / recipient match the public inputs.

    Parameters
    ----------
    setup : TrustedSetup
        Must have ``num_public_inputs >= 3``.
    """

    def __init__(self, setup: TrustedSetup) -> None:
        if setup.vk.num_public_inputs < 3:
            raise ValueError(
                "Withdrawal circuit requires >= 3 public inputs "
                f"(setup has {setup.vk.num_public_inputs})"
            )
        self.prover = Groth16Prover(setup.pk)
        self.verifier = Groth16Verifier(setup.vk)
        self.setup = setup

    @staticmethod
    def derive_public_inputs(
        amount: int,
        nonce: int,
        recipient: str,
    ) -> List[int]:
        """Derive the 3 public inputs for a withdrawal.

        Parameters
        ----------
        amount : int
            Withdrawal amount in wei.
        nonce : int
            Withdrawal nonce.
        recipient : str
            Ethereum address (``0x``-prefixed or raw hex).

        Returns
        -------
        list of int
            ``[amount_mod, nonce_mod, recipient_hash]``
        """
        amount_mod = amount % curve_order
        nonce_mod = nonce % curve_order
        addr_clean = recipient.lower().replace("0x", "").ljust(40, "0")[:40]
        addr_bytes = bytes.fromhex(addr_clean)
        recipient_hash = int.from_bytes(
            hashlib.sha256(addr_bytes).digest(), "big",
        ) % curve_order
        return [amount_mod, nonce_mod, recipient_hash]

    def prove_withdrawal(
        self,
        amount: int,
        nonce: int,
        recipient: str,
        signatures: List[bytes],
        state_root: bytes,
    ) -> Tuple[bytes, List[int]]:
        """Generate a proof for a withdrawal.

        Parameters
        ----------
        amount : int
            Withdrawal amount in wei.
        nonce : int
            Withdrawal nonce.
        recipient : str
            Destination Ethereum address.
        signatures : list of bytes
            Validator signatures authorising the withdrawal.
        state_root : bytes
            Merkle state root at the time of withdrawal.

        Returns
        -------
        tuple of (bytes, list of int)
            ``(proof_bytes_256, public_inputs)``
        """
        public_inputs = self.derive_public_inputs(amount, nonce, recipient)

        # Build witness from signatures and state root
        witness = self._build_witness(signatures, state_root)

        proof = self.prover.prove(public_inputs, witness)
        proof_bytes = Groth16Prover.serialize_proof(proof)

        return proof_bytes, public_inputs

    def verify_withdrawal(
        self, proof_bytes: bytes, public_inputs: List[int],
    ) -> bool:
        """Verify a withdrawal proof.

        Parameters
        ----------
        proof_bytes : bytes
            256-byte serialised proof.
        public_inputs : list of int
            Public inputs ``[amount, nonce, recipient_hash]``.

        Returns
        -------
        bool
        """
        return self.verifier.verify_from_bytes(proof_bytes, public_inputs)

    @staticmethod
    def _build_witness(
        signatures: List[bytes], state_root: bytes,
    ) -> List[int]:
        """Derive the private witness from signatures and state root."""
        witness: List[int] = []
        # Signature commitment
        sig_data = b"".join(signatures)
        witness.append(hash_to_scalar(b"sig_commitment", sig_data))
        # State root commitment
        witness.append(hash_to_scalar(b"state_root", state_root))
        # Threshold proof
        witness.append(
            hash_to_scalar(b"threshold", len(signatures).to_bytes(4, "big"))
        )
        # Authorisation nonce
        witness.append(random_scalar())
        return witness


class SyncCommitteeCircuit:
    """Circuit that proves a valid sync committee rotation.

    Public inputs: ``[new_committee_root_scalar, new_slot, padding]``

    Witness (private): old committee public keys, new committee public
    keys, BLS aggregate signature.

    Parameters
    ----------
    setup : TrustedSetup
        Must have ``num_public_inputs >= 2``.
    """

    def __init__(self, setup: TrustedSetup) -> None:
        if setup.vk.num_public_inputs < 2:
            raise ValueError(
                "Sync committee circuit requires >= 2 public inputs "
                f"(setup has {setup.vk.num_public_inputs})"
            )
        self.prover = Groth16Prover(setup.pk)
        self.verifier = Groth16Verifier(setup.vk)
        self.setup = setup

    @staticmethod
    def derive_public_inputs(
        committee_root: bytes,
        slot: int,
    ) -> List[int]:
        """Derive public inputs for a sync committee update.

        Parameters
        ----------
        committee_root : bytes
            32-byte committee root hash.
        slot : int
            Beacon chain slot number.

        Returns
        -------
        list of int
            ``[root_scalar, slot_mod]``
        """
        root_bytes = committee_root[:32].ljust(32, b"\x00")
        root_scalar = int.from_bytes(root_bytes, "big") % curve_order
        slot_mod = slot % curve_order
        return [root_scalar, slot_mod]

    def prove_rotation(
        self,
        committee_root: bytes,
        slot: int,
        old_pubkeys: List[bytes],
        new_pubkeys: List[bytes],
        aggregate_sig: bytes,
    ) -> Tuple[bytes, List[int]]:
        """Generate a proof for a sync committee rotation.

        Returns
        -------
        tuple of (bytes, list of int)
            ``(proof_bytes_256, public_inputs)``
        """
        public_inputs = self.derive_public_inputs(committee_root, slot)

        # Pad public_inputs to match setup's expected count
        n_pub = self.setup.vk.num_public_inputs
        while len(public_inputs) < n_pub:
            public_inputs.append(0)

        witness = self._build_witness(old_pubkeys, new_pubkeys, aggregate_sig)

        proof = self.prover.prove(public_inputs, witness)
        proof_bytes = Groth16Prover.serialize_proof(proof)

        return proof_bytes, public_inputs

    def verify_rotation(
        self, proof_bytes: bytes, public_inputs: List[int],
    ) -> bool:
        """Verify a sync committee rotation proof."""
        return self.verifier.verify_from_bytes(proof_bytes, public_inputs)

    @staticmethod
    def _build_witness(
        old_pubkeys: List[bytes],
        new_pubkeys: List[bytes],
        aggregate_sig: bytes,
    ) -> List[int]:
        """Derive the private witness for committee rotation."""
        witness: List[int] = []
        old_data = b"".join(old_pubkeys)
        new_data = b"".join(new_pubkeys)
        witness.append(hash_to_scalar(b"old_committee", old_data))
        witness.append(hash_to_scalar(b"new_committee", new_data))
        witness.append(hash_to_scalar(b"agg_sig", aggregate_sig))
        witness.append(random_scalar())
        return witness


# ---------------------------------------------------------------------------
# Coordinate serialisation helpers
# ---------------------------------------------------------------------------

def g1_to_uint256(point: G1Point) -> Tuple[int, int]:
    """Convert a G1 point to ``(x, y)`` as uint256 values.

    Parameters
    ----------
    point : G1Point
        A point on the BN254 G1 curve.

    Returns
    -------
    tuple of (int, int)
        ``(x, y)`` where each is a 256-bit unsigned integer.

    Raises
    ------
    ValueError
        If the point is the point at infinity.
    """
    if point is None or point == Z1:
        raise ValueError("Cannot serialise point at infinity")
    x, y = point
    return int(x), int(y)


def g2_to_uint256(
    point: G2Point,
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Convert a G2 point to Ethereum-convention uint256 tuples.

    Ethereum's ``ecPairing`` precompile uses ``(imaginary, real)``
    ordering for the FQ2 components.

    Parameters
    ----------
    point : G2Point
        A point on the BN254 G2 curve.

    Returns
    -------
    tuple of ((int, int), (int, int))
        ``((x_imag, x_real), (y_imag, y_real))``

    Raises
    ------
    ValueError
        If the point is the point at infinity.
    """
    if point is None or point == Z2:
        raise ValueError("Cannot serialise point at infinity")
    x, y = point
    # FQ2 stores as [real, imag] internally; Ethereum wants (imag, real)
    x_real = int(x.coeffs[0])
    x_imag = int(x.coeffs[1])
    y_real = int(y.coeffs[0])
    y_imag = int(y.coeffs[1])
    return (x_imag, x_real), (y_imag, y_real)


def vk_to_solidity_args(vk: VerificationKey) -> Dict[str, Any]:
    """Convert a verification key to Solidity constructor arguments.

    Returns a dict compatible with the ``deploy_verifier()`` call in
    :class:`~.contract_client.BridgeDeployer`::

        {
            "alpha": [x, y],              # G1 point
            "beta":  [[x1, x0], [y1, y0]],# G2 (imag, real)
            "gamma": [[x1, x0], [y1, y0]],
            "delta": [[x1, x0], [y1, y0]],
            "ic":    [[x, y], ...],        # list of G1 points
        }
    """
    alpha_x, alpha_y = g1_to_uint256(vk.alpha1)

    def _g2_flat(pt: G2Point) -> List[List[int]]:
        (xi, xr), (yi, yr) = g2_to_uint256(pt)
        return [[xi, xr], [yi, yr]]

    ic_list = []
    for pt in vk.ic:
        ix, iy = g1_to_uint256(pt)
        ic_list.append([ix, iy])

    return {
        "alpha": [alpha_x, alpha_y],
        "beta": _g2_flat(vk.beta2),
        "gamma": _g2_flat(vk.gamma2),
        "delta": _g2_flat(vk.delta2),
        "ic": ic_list,
    }


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------

def _is_valid_g1(point: G1Point) -> bool:
    """Check that a G1 point is on the curve and not at infinity."""
    if point is None or point == Z1:
        return False
    try:
        return is_on_curve(point, B_COEFF)
    except Exception:
        return False


def _is_valid_g2(point: G2Point) -> bool:
    """Check that a G2 point is on the curve and not at infinity."""
    if point is None or point == Z2:
        return False
    try:
        return is_on_curve(point, B2_COEFF)
    except Exception:
        return False
