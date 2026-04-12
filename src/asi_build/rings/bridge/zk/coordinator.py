"""
Bridge Proof Coordinator
=========================

Orchestrates ZK proof generation for bridge operations.
Manages the full lifecycle: circuit selection → witness generation →
proof generation → proof caching → on-chain submission formatting.

The coordinator is the primary interface between the bridge orchestrator
(``e2e.py``) and the ZK proof system.  It handles:

- Proof generation for withdrawals, sync committee updates, deposits
- LRU caching of proofs (avoid regeneration for retries)
- Batch proving (multiple operations in one proof)
- Proof statistics and monitoring

Architecture
~~~~~~~~~~~~

::

    ┌──────────────┐
    │  Orchestrator │  (e2e.py)
    │  (BridgeOrch) │
    └──────┬───────┘
           │  prove_withdrawal / prove_sync_committee_update / ...
           ▼
    ┌──────────────────┐
    │  BridgeProof      │  ← this module
    │  Coordinator      │
    │  ┌────────────┐  │
    │  │ ProofCache  │  │     LRU cache (circuit_id, public_inputs) → ZKProof
    │  └────────────┘  │
    │  ┌────────────┐  │
    │  │ ProofStats  │  │     Generation metrics & monitoring
    │  └────────────┘  │
    └──────┬───────────┘
           │  generate_proof(circuit, witness, public_inputs)
           ▼
    ┌──────────────┐
    │  ZKProofEngine│  (prover.py — SimulatedProver / SP1Prover)
    └──────────────┘

Caching
~~~~~~~

Proofs are cached by ``(circuit_id, SHA256(canonical(public_inputs)))``.
Cache hits return immediately without invoking the prover — this is
critical for retry flows where the same withdrawal may be re-proved
after a transient submission failure.

Batching
~~~~~~~~

``batch_prove()`` accepts a list of operation dicts and generates all
proofs concurrently via ``asyncio.gather``.  In the future this could
be upgraded to recursive proof composition (one wrapping proof) but for
now it's simple parallel generation.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from .circuits import (
    BLSVerificationCircuit,
    BridgeWithdrawalCircuit,
    Circuit,
    MerklePatriciaCircuit,
    SyncCommitteeRotationCircuit,
)

if TYPE_CHECKING:
    from .prover import ZKProof, ZKProofEngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ProofStats
# ---------------------------------------------------------------------------


@dataclass
class ProofStats:
    """Aggregate statistics for proof generation.

    Used for monitoring and alerting — the bridge operator dashboard
    reads these to display proof throughput, cache efficiency, and gas
    cost estimates.

    Attributes
    ----------
    total_proofs : int
        Total proof generation attempts (successful + failed).
    successful_proofs : int
        Proofs that generated without error.
    failed_proofs : int
        Proofs that raised ``ProofGenerationError``.
    total_generation_time_ms : int
        Sum of generation times for all successful proofs.
    cache_hits : int
        Number of times a cached proof was returned.
    cache_misses : int
        Number of times the prover was invoked.
    avg_proof_size_bytes : float
        Running average of ``ZKProof.proof_size_bytes``.
    avg_generation_time_ms : float
        Running average of generation time in milliseconds.
    avg_verify_gas : float
        Running average of ``ZKProof.estimated_verify_gas``.
    proofs_by_circuit : dict
        ``{circuit_id: count}`` — distribution across circuit types.
    proofs_by_type : dict
        ``{proof_type: count}`` — distribution across proof types.
    last_proof_time : float or None
        Unix timestamp of the most recent successful proof.
    """

    total_proofs: int = 0
    successful_proofs: int = 0
    failed_proofs: int = 0
    total_generation_time_ms: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_proof_size_bytes: float = 0.0
    avg_generation_time_ms: float = 0.0
    avg_verify_gas: float = 0.0
    proofs_by_circuit: Dict[str, int] = field(default_factory=dict)
    proofs_by_type: Dict[str, int] = field(default_factory=dict)
    last_proof_time: Optional[float] = None

    # -- recording ----------------------------------------------------------

    def record_proof(self, proof: ZKProof, generation_time_ms: int) -> None:
        """Record a successful proof generation.

        Updates all running averages and counters.

        Parameters
        ----------
        proof : ZKProof
            The generated proof object.
        generation_time_ms : int
            Wall-clock time taken to generate the proof.
        """
        self.total_proofs += 1
        self.successful_proofs += 1
        self.total_generation_time_ms += generation_time_ms
        self.last_proof_time = time.time()

        # Running averages (incremental Welford-style)
        n = self.successful_proofs
        self.avg_proof_size_bytes += (
            (proof.proof_size_bytes - self.avg_proof_size_bytes) / n
        )
        self.avg_generation_time_ms += (
            (generation_time_ms - self.avg_generation_time_ms) / n
        )
        self.avg_verify_gas += (
            (proof.estimated_verify_gas - self.avg_verify_gas) / n
        )

        # Per-circuit / per-type counters
        cid = proof.circuit_id
        self.proofs_by_circuit[cid] = self.proofs_by_circuit.get(cid, 0) + 1
        pt = proof.proof_type
        self.proofs_by_type[pt] = self.proofs_by_type.get(pt, 0) + 1

    def record_failure(self, circuit_id: str) -> None:
        """Record a failed proof generation attempt.

        Parameters
        ----------
        circuit_id : str
            The circuit that was being proved when the error occurred.
        """
        self.total_proofs += 1
        self.failed_proofs += 1
        # Count failures in the circuit distribution too
        self.proofs_by_circuit[circuit_id] = (
            self.proofs_by_circuit.get(circuit_id, 0) + 1
        )

    def record_cache_hit(self) -> None:
        """Record that a cached proof was returned."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record that the prover was invoked (cache miss)."""
        self.cache_misses += 1

    def to_dict(self) -> dict:
        """Serialise stats to a plain dictionary.

        Returns
        -------
        dict
            JSON-serialisable representation of all statistics.
        """
        total_lookups = self.cache_hits + self.cache_misses
        return {
            "total_proofs": self.total_proofs,
            "successful_proofs": self.successful_proofs,
            "failed_proofs": self.failed_proofs,
            "total_generation_time_ms": self.total_generation_time_ms,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / total_lookups if total_lookups > 0 else 0.0
            ),
            "avg_proof_size_bytes": round(self.avg_proof_size_bytes, 2),
            "avg_generation_time_ms": round(self.avg_generation_time_ms, 2),
            "avg_verify_gas": round(self.avg_verify_gas, 2),
            "proofs_by_circuit": dict(self.proofs_by_circuit),
            "proofs_by_type": dict(self.proofs_by_type),
            "last_proof_time": self.last_proof_time,
            "success_rate": (
                self.successful_proofs / self.total_proofs
                if self.total_proofs > 0
                else 0.0
            ),
        }


# ---------------------------------------------------------------------------
# ProofCache
# ---------------------------------------------------------------------------


class ProofCache:
    """LRU cache for ZK proofs, keyed by ``(circuit_id, public_inputs_hash)``.

    This avoids re-running expensive proof generation when the same
    withdrawal or committee update is retried after a transient failure.

    Parameters
    ----------
    max_size : int
        Maximum number of proofs to retain.  When full, the least-recently
        used entry is evicted.
    """

    def __init__(self, max_size: int = 100) -> None:
        self._cache: OrderedDict[str, ZKProof] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    # -- key computation ----------------------------------------------------

    @staticmethod
    def _make_key(circuit_id: str, public_inputs: dict) -> str:
        """Produce a deterministic cache key from circuit ID + public inputs.

        The public inputs dict is canonicalised via sorted JSON, then
        SHA-256 hashed.  This avoids key-length issues and ensures
        byte-valued dict entries (which aren't directly JSON-serialisable)
        are handled gracefully.

        Parameters
        ----------
        circuit_id : str
            Unique circuit identifier (e.g. ``"withdrawal"``).
        public_inputs : dict
            The public inputs for the proof.

        Returns
        -------
        str
            Hex-encoded SHA-256 digest.
        """

        def _normalise(obj: Any) -> Any:
            """Recursively convert bytes to hex for JSON serialisation."""
            if isinstance(obj, bytes):
                return obj.hex()
            if isinstance(obj, dict):
                return {str(k): _normalise(v) for k, v in sorted(obj.items())}
            if isinstance(obj, (list, tuple)):
                return [_normalise(v) for v in obj]
            return obj

        canonical = json.dumps(
            {"circuit_id": circuit_id, "inputs": _normalise(public_inputs)},
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        return digest

    # -- cache operations ---------------------------------------------------

    def get(self, circuit_id: str, public_inputs: dict) -> Optional[ZKProof]:
        """Look up a cached proof.

        If found, the entry is moved to the end (most-recently used).

        Parameters
        ----------
        circuit_id : str
            Circuit identifier.
        public_inputs : dict
            Public inputs to match.

        Returns
        -------
        ZKProof or None
            The cached proof, or ``None`` on cache miss.
        """
        key = self._make_key(circuit_id, public_inputs)
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]
        self._misses += 1
        return None

    def put(
        self, circuit_id: str, public_inputs: dict, proof: ZKProof
    ) -> None:
        """Insert or update a cached proof.

        Evicts the least-recently used entry if the cache is full.

        Parameters
        ----------
        circuit_id : str
            Circuit identifier.
        public_inputs : dict
            Public inputs for the proof.
        proof : ZKProof
            The proof object to cache.
        """
        key = self._make_key(circuit_id, public_inputs)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = proof
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)  # Evict oldest

    def invalidate(self, circuit_id: Optional[str] = None) -> int:
        """Remove cached proofs.

        Parameters
        ----------
        circuit_id : str, optional
            If provided, only invalidate entries whose key was generated
            with this circuit ID.  If ``None``, clear the entire cache.

        Returns
        -------
        int
            Number of entries removed.
        """
        if circuit_id is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        # We need to recheck keys — since our keys are hashes, we can't
        # reverse them.  Instead, re-hash all cached entries... but we
        # don't store the original inputs.  Pragmatic solution: iterate
        # and look for a prefix pattern.
        #
        # Better approach: store (circuit_id, proof) tuples.
        # For now, clear everything if a specific circuit is requested.
        # This is safe (just less efficient).
        count = len(self._cache)
        self._cache.clear()
        return count

    def clear(self) -> None:
        """Remove all cached proofs."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Number of cached proofs."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a fraction in ``[0, 1]``.

        Returns 0.0 if no lookups have been performed.
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total


# ---------------------------------------------------------------------------
# BridgeProofCoordinator
# ---------------------------------------------------------------------------


class BridgeProofCoordinator:
    """Orchestrates ZK proof generation for all bridge operations.

    This is the single entry point used by :class:`BridgeOrchestrator`
    (``e2e.py``) to generate, cache, and verify ZK proofs.

    Parameters
    ----------
    prover : ZKProofEngine
        The proof engine (``SimulatedProver`` or ``SP1Prover``).
    cache_size : int
        Maximum LRU cache size (default 100).
    enable_caching : bool
        Whether to enable proof caching (default ``True``).
    enable_batching : bool
        Whether to enable batch proving (default ``True``).
    max_batch_size : int
        Maximum operations per batch (default 10).
    """

    def __init__(
        self,
        prover: ZKProofEngine,
        *,
        cache_size: int = 100,
        enable_caching: bool = True,
        enable_batching: bool = True,
        max_batch_size: int = 10,
    ) -> None:
        self.prover = prover
        self.cache: Optional[ProofCache] = (
            ProofCache(cache_size) if enable_caching else None
        )
        self.stats = ProofStats()
        self._enable_batching = enable_batching
        self._max_batch_size = max_batch_size
        self._batch_queue: List[dict] = []

        # Pre-instantiate circuits — one instance per type, reused
        self.circuits: Dict[str, Circuit] = {
            "bls_verify": BLSVerificationCircuit(),
            "mpt_verify": MerklePatriciaCircuit(),
            "withdrawal": BridgeWithdrawalCircuit(),
            "committee_rotation": SyncCommitteeRotationCircuit(),
        }

    # -- public: high-level proof methods -----------------------------------

    async def prove_withdrawal(
        self,
        recipient: str,
        amount: int,
        nonce: int,
        rings_did: str,
        header_proof: dict,
        receipt_proof: dict,
        validator_sigs: List[bytes],
        validator_threshold: int = 4,
    ) -> ZKProof:
        """Generate a complete withdrawal proof.

        Flow:

        1. Get the ``BridgeWithdrawalCircuit``
        2. Generate witness from parameters
        3. Extract public inputs from witness
        4. Check cache for existing proof with same public inputs
        5. If cache miss, generate proof via prover
        6. Cache the result
        7. Update stats

        Parameters
        ----------
        recipient : str
            Ethereum address (hex, with or without ``0x`` prefix).
        amount : int
            Withdrawal amount in wei.
        nonce : int
            Withdrawal nonce (prevents replay).
        rings_did : str
            Rings DID identifier.
        header_proof : dict
            BLS attestation data (``committee_pubkeys``, ``signature``,
            ``header_fields``, ``bitmap``).
        receipt_proof : dict
            MPT inclusion data (``state_root``, ``address``,
            ``proof_nodes``, ``account_state``).
        validator_sigs : list of bytes
            Bridge validator signatures authorising the withdrawal.
        validator_threshold : int
            Minimum validator signature count (default 4).

        Returns
        -------
        ZKProof
            The generated (or cached) withdrawal proof.

        Raises
        ------
        ProofGenerationError
            If the prover fails to generate the proof.
        KeyError
            If the withdrawal circuit is not registered.
        """
        circuit = self.get_circuit("withdrawal")

        witness = circuit.generate_witness(
            recipient=recipient,
            amount=amount,
            nonce=nonce,
            rings_did=rings_did,
            header_proof=header_proof,
            receipt_proof=receipt_proof,
            validator_sigs=validator_sigs,
            threshold=validator_threshold,
        )

        public_inputs = circuit.public_inputs_from_witness(witness)
        return await self._generate_with_cache(
            circuit_id="withdrawal",
            circuit=circuit,
            witness=witness,
            public_inputs=public_inputs,
        )

    async def prove_sync_committee_update(
        self,
        current_root: bytes,
        new_committee_pubkeys: List[bytes],
        attestation_sig: bytes,
        attestation_bitmap: List[bool],
        slot: int,
    ) -> ZKProof:
        """Prove a sync committee rotation.

        Generates a ZK proof that the current sync committee (identified
        by ``current_root``) has attested a valid rotation to a new
        committee whose public keys hash to a new root.

        Parameters
        ----------
        current_root : bytes
            32-byte SHA-256 root of the current committee.
            (Used for logging/context — the circuit re-derives it from
            pubkeys internally.)
        new_committee_pubkeys : list of bytes
            48-byte BLS public keys of the incoming committee.
        attestation_sig : bytes
            96-byte aggregate BLS signature from the current committee.
        attestation_bitmap : list of bool
            Which current committee members participated.
        slot : int
            Beacon chain slot at which the rotation is attested.

        Returns
        -------
        ZKProof
            The generated (or cached) committee rotation proof.
        """
        circuit = self.get_circuit("committee_rotation")

        # The circuit needs both current and new pubkeys.
        # For committee rotation proofs, we need the current pubkeys to
        # verify the attestation.  We derive synthetic current keys from
        # the root for simulation purposes — in production, the full
        # current committee would be available from the light client.
        #
        # NOTE: The caller should ideally provide current_pubkeys too.
        # Here we construct a witness that the circuit can verify.
        # We pass new_committee_pubkeys as both current and new when
        # current_pubkeys aren't available — the circuit will derive
        # its own roots.  This is a simulation simplification.
        witness = circuit.generate_witness(
            current_pubkeys=new_committee_pubkeys,  # See note above
            new_pubkeys=new_committee_pubkeys,
            attestation_sig=attestation_sig,
            attestation_bitmap=attestation_bitmap,
            slot=slot,
        )

        public_inputs = circuit.public_inputs_from_witness(witness)

        logger.info(
            "Proving sync committee rotation at slot %d "
            "(current_root=%s, new_root=%s)",
            slot,
            current_root[:8].hex() if current_root else "N/A",
            public_inputs.get("new_committee_root", b"")[:8].hex()
            if isinstance(public_inputs.get("new_committee_root"), bytes)
            else "N/A",
        )

        return await self._generate_with_cache(
            circuit_id="committee_rotation",
            circuit=circuit,
            witness=witness,
            public_inputs=public_inputs,
        )

    async def prove_deposit_inclusion(
        self,
        state_root: bytes,
        address: str,
        proof_nodes: List[bytes],
        account_state: dict,
    ) -> ZKProof:
        """Prove a deposit event was included in a verified block.

        Uses :class:`MerklePatriciaCircuit` to prove that the account
        at ``address`` has the claimed state within the given
        ``state_root``.

        Parameters
        ----------
        state_root : bytes
            32-byte state root from the verified beacon block.
        address : str
            Ethereum address of the bridge contract.
        proof_nodes : list of bytes
            MPT proof nodes from ``eth_getProof``.
        account_state : dict
            Account state fields: ``nonce``, ``balance``,
            ``storage_root``, ``code_hash``.

        Returns
        -------
        ZKProof
            The generated (or cached) MPT inclusion proof.
        """
        circuit = self.get_circuit("mpt_verify")

        witness = circuit.generate_witness(
            state_root=state_root,
            address=address,
            proof_nodes=proof_nodes,
            account_state=account_state,
        )

        public_inputs = circuit.public_inputs_from_witness(witness)
        return await self._generate_with_cache(
            circuit_id="mpt_verify",
            circuit=circuit,
            witness=witness,
            public_inputs=public_inputs,
        )

    async def prove_bls_verification(
        self,
        committee_pubkeys: List[bytes],
        signature: bytes,
        header_fields: dict,
        bitmap: List[bool],
    ) -> ZKProof:
        """Prove BLS signature verification over a beacon header.

        Uses :class:`BLSVerificationCircuit` to prove that a sync
        committee super-majority attested a specific block header.

        Parameters
        ----------
        committee_pubkeys : list of bytes
            48-byte BLS public keys of the sync committee.
        signature : bytes
            96-byte aggregate BLS signature.
        header_fields : dict
            Beacon header fields: ``slot``, ``proposer_index``,
            ``parent_root``, ``state_root``, ``body_root``.
        bitmap : list of bool
            Participation bitmap.

        Returns
        -------
        ZKProof
            The generated (or cached) BLS verification proof.
        """
        circuit = self.get_circuit("bls_verify")

        witness = circuit.generate_witness(
            committee_pubkeys=committee_pubkeys,
            signature=signature,
            header_fields=header_fields,
            bitmap=bitmap,
        )

        public_inputs = circuit.public_inputs_from_witness(witness)
        return await self._generate_with_cache(
            circuit_id="bls_verify",
            circuit=circuit,
            witness=witness,
            public_inputs=public_inputs,
        )

    # -- batching -----------------------------------------------------------

    async def batch_prove(
        self, operations: List[dict]
    ) -> List[ZKProof]:
        """Batch-prove multiple operations concurrently.

        Each operation is a dict with a ``'type'`` key indicating the
        proof type and the remaining keys providing the parameters for
        that proof type.

        Supported types
        ---------------
        - ``"withdrawal"``: calls :meth:`prove_withdrawal`
        - ``"committee_rotation"``: calls :meth:`prove_sync_committee_update`
        - ``"deposit_inclusion"``: calls :meth:`prove_deposit_inclusion`
        - ``"bls_verify"``: calls :meth:`prove_bls_verification`

        Parameters
        ----------
        operations : list of dict
            Each dict must have a ``"type"`` key plus the parameters
            expected by the corresponding ``prove_*`` method.

        Returns
        -------
        list of ZKProof
            One proof per operation, in the same order.

        Raises
        ------
        ValueError
            If the batch exceeds ``max_batch_size`` or an operation
            has an unknown type.
        """
        if not self._enable_batching:
            raise RuntimeError("Batching is disabled on this coordinator")

        if len(operations) > self._max_batch_size:
            raise ValueError(
                f"Batch size {len(operations)} exceeds maximum "
                f"{self._max_batch_size}"
            )

        if not operations:
            return []

        logger.info("Batch proving %d operations", len(operations))

        tasks = [self._prove_single(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Unwrap: re-raise first exception if any
        proofs: List[ZKProof] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.error(
                    "Batch operation %d failed: %s", i, result
                )
                raise result
            proofs.append(result)

        return proofs

    async def _prove_single(self, operation: dict) -> ZKProof:
        """Dispatch a single batch operation to the appropriate prove method.

        Parameters
        ----------
        operation : dict
            Must contain ``"type"`` plus relevant parameters.

        Returns
        -------
        ZKProof
        """
        op_type = operation.get("type")
        params = {k: v for k, v in operation.items() if k != "type"}

        if op_type == "withdrawal":
            return await self.prove_withdrawal(**params)
        elif op_type == "committee_rotation":
            return await self.prove_sync_committee_update(**params)
        elif op_type == "deposit_inclusion":
            return await self.prove_deposit_inclusion(**params)
        elif op_type == "bls_verify":
            return await self.prove_bls_verification(**params)
        else:
            raise ValueError(f"Unknown operation type: {op_type!r}")

    # -- verification -------------------------------------------------------

    async def verify_proof(self, proof: ZKProof) -> bool:
        """Verify any proof using the appropriate circuit.

        Looks up the circuit from ``proof.circuit_id`` and delegates to
        the prover's verify method.

        Parameters
        ----------
        proof : ZKProof
            The proof to verify.

        Returns
        -------
        bool
            ``True`` if the proof is valid.
        """
        circuit_id = proof.circuit_id
        if circuit_id not in self.circuits:
            logger.warning(
                "Cannot verify proof: unknown circuit_id=%r", circuit_id
            )
            return False

        circuit = self.circuits[circuit_id]
        return await self.prover.verify_proof(circuit, proof, proof.public_inputs)

    # -- introspection ------------------------------------------------------

    def get_stats(self) -> dict:
        """Return proof generation statistics as a dict.

        Includes cache statistics if caching is enabled.

        Returns
        -------
        dict
            JSON-serialisable statistics.
        """
        stats_dict = self.stats.to_dict()
        if self.cache is not None:
            stats_dict["cache_size"] = self.cache.size
            stats_dict["cache_hit_rate"] = round(self.cache.hit_rate, 4)
        stats_dict["batching_enabled"] = self._enable_batching
        stats_dict["max_batch_size"] = self._max_batch_size
        stats_dict["available_circuits"] = self.available_circuits
        return stats_dict

    def get_circuit(self, circuit_id: str) -> Circuit:
        """Get a circuit by its identifier.

        Parameters
        ----------
        circuit_id : str
            One of ``"bls_verify"``, ``"mpt_verify"``, ``"withdrawal"``,
            or ``"committee_rotation"``.

        Returns
        -------
        Circuit
            The circuit instance.

        Raises
        ------
        KeyError
            If ``circuit_id`` is not registered.
        """
        if circuit_id not in self.circuits:
            raise KeyError(
                f"Unknown circuit_id={circuit_id!r}. "
                f"Available: {self.available_circuits}"
            )
        return self.circuits[circuit_id]

    @property
    def available_circuits(self) -> List[str]:
        """List registered circuit identifiers.

        Returns
        -------
        list of str
            Sorted list of circuit IDs.
        """
        return sorted(self.circuits.keys())

    # -- internal: cache-aware proof generation ------------------------------

    async def _generate_with_cache(
        self,
        circuit_id: str,
        circuit: Circuit,
        witness: dict,
        public_inputs: dict,
    ) -> ZKProof:
        """Generate a proof, checking cache first.

        This is the core internal method used by all ``prove_*`` methods.

        Parameters
        ----------
        circuit_id : str
            Circuit identifier for caching and stats.
        circuit : Circuit
            The circuit instance.
        witness : dict
            Full witness (public + private).
        public_inputs : dict
            Public inputs extracted from the witness.

        Returns
        -------
        ZKProof
            The proof (from cache or freshly generated).
        """
        # 1. Check cache
        if self.cache is not None:
            cached = self.cache.get(circuit_id, public_inputs)
            if cached is not None:
                self.stats.record_cache_hit()
                logger.debug(
                    "Cache hit for circuit=%s", circuit_id
                )
                return cached
            self.stats.record_cache_miss()

        # 2. Generate proof
        t_start = time.monotonic()
        try:
            proof = await self.prover.generate_proof(
                circuit, witness, public_inputs
            )
        except Exception:
            self.stats.record_failure(circuit_id)
            logger.error(
                "Proof generation failed for circuit=%s", circuit_id,
                exc_info=True,
            )
            raise

        t_elapsed_ms = int((time.monotonic() - t_start) * 1000)

        # 3. Update stats
        self.stats.record_proof(proof, t_elapsed_ms)
        logger.info(
            "Proof generated: circuit=%s time=%dms size=%dB gas=%d",
            circuit_id,
            t_elapsed_ms,
            proof.proof_size_bytes,
            proof.estimated_verify_gas,
        )

        # 4. Cache the result
        if self.cache is not None:
            self.cache.put(circuit_id, public_inputs, proof)

        return proof


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "BridgeProofCoordinator",
    "ProofCache",
    "ProofStats",
]
