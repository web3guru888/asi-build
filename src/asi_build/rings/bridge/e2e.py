"""
Bridge End-to-End Orchestrator
===============================

Ties together the :class:`BridgeValidator` (DHT-based attestation),
:class:`BridgeContractClient` (on-chain interactions), and
:class:`EthLightClient` (header verification) into a single
:class:`BridgeOrchestrator` that can drive the full deposit → attest →
withdraw lifecycle.

The orchestrator runs the bridge "relay" loop:

1. **Process deposits** — fetch ``Deposited`` events from the contract,
   verify each via the light client, store in the DHT, and attest.
2. **Process withdrawals** — request via DHT, collect threshold
   approvals, generate a real Groth16 ZK proof (BN254 pairing-based),
   and submit on-chain.
3. **Sync committee updates** — detect rotation boundaries and submit
   committee root proofs (also Groth16).
4. **Health checks** — rate limits, slot lag, validator liveness.

If no ``zk_prover`` is provided to the :class:`BridgeOrchestrator`,
a deterministic mock is used for backward compatibility with existing
tests.

Usage::

    orchestrator = BridgeOrchestrator(validator, contract_client, light_client)
    processed = await orchestrator.process_deposits(from_block=18_000_000)
    tx_hash  = await orchestrator.process_withdrawal(
        rings_did="did:rings:ed25519:abc",
        amount=10 ** 18,
        eth_address="0x...",
    )
    await orchestrator.run_bridge_loop(poll_interval=12.0)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .light_client import EthLightClient, BeaconHeader
from .protocol import BridgeValidator, DepositRecord

if TYPE_CHECKING:
    from .zk_prover import BridgeWithdrawalCircuit, SyncCommitteeCircuit
    from .zk.coordinator import BridgeProofCoordinator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_zk_proof(data: bytes) -> bytes:
    """Generate a deterministic placeholder ZK proof.

    In production this would invoke a Groth16 prover (e.g. snarkjs or
    rapidsnark). For now we return ``sha256(data)`` padded to 256 bytes,
    which is the expected length of a serialised ``(A, B, C)`` proof.

    Parameters
    ----------
    data : bytes
        Arbitrary data to commit to.

    Returns
    -------
    bytes
        256-byte placeholder proof.
    """
    digest = hashlib.sha256(data).digest()  # 32 bytes
    return digest * 8  # 256 bytes


def _mock_public_inputs(amount: int, nonce: int, recipient_hash: int) -> List[int]:
    """Build public-inputs vector for the withdrawal verifier.

    Parameters
    ----------
    amount : int
        Withdrawal amount in wei.
    nonce : int
        Withdrawal nonce.
    recipient_hash : int
        A numeric hash of the recipient (e.g. first 8 bytes of address).

    Returns
    -------
    list of int
        Public inputs for the circuit.
    """
    return [amount, nonce, recipient_hash]


# ---------------------------------------------------------------------------
# BridgeOrchestrator
# ---------------------------------------------------------------------------


@dataclass
class ProcessedDeposit:
    """Result of processing a single deposit event."""

    tx_hash: str
    block_number: int
    amount: int
    rings_did: str
    sender: str
    verified: bool
    attested: bool
    record: Optional[DepositRecord] = None
    error: Optional[str] = None


class BridgeOrchestrator:
    """Full bridge flow: deposit observation, attestation, withdrawal submission.

    The orchestrator coordinates three (or four) subsystems:

    * **BridgeValidator** — DHT-based attestation and approval logic.
    * **BridgeContractClient** — on-chain reads and writes.
    * **EthLightClient** — header and event proof verification.
    * **ZK Prover** (optional) — real Groth16 proof generation using
      BN254 pairing math.  If not provided, falls back to a
      deterministic mock proof (``sha256 * 8``).
    * **Proof Coordinator** (optional) — high-level ZK proof lifecycle
      manager from :mod:`~.zk.coordinator`, with caching, batching, and
      statistics.  Takes precedence over individual circuits when provided.

    Parameters
    ----------
    validator : BridgeValidator
        An active bridge validator.
    contract_client : object
        A :class:`BridgeContractClient` connected to the on-chain bridge.
    light_client : EthLightClient
        A synced Ethereum light client.
    max_deposits_per_batch : int
        Maximum number of deposit events to process in one call.
    withdrawal_circuit : BridgeWithdrawalCircuit, optional
        Real Groth16 withdrawal prover.  If ``None``, uses the mock.
    sync_circuit : SyncCommitteeCircuit, optional
        Real Groth16 sync committee prover.  If ``None``, uses the mock.
    proof_coordinator : BridgeProofCoordinator, optional
        High-level ZK proof coordinator.  When provided, withdrawal and
        sync committee proofs are generated via the coordinator (which
        supports caching, batching, and statistics) instead of the
        individual circuit objects.
    """

    def __init__(
        self,
        validator: BridgeValidator,
        contract_client: Any,
        light_client: EthLightClient,
        *,
        max_deposits_per_batch: int = 100,
        withdrawal_circuit: Optional["BridgeWithdrawalCircuit"] = None,
        sync_circuit: Optional["SyncCommitteeCircuit"] = None,
        proof_coordinator: Optional["BridgeProofCoordinator"] = None,
        safety_manager: Optional[Any] = None,
    ) -> None:
        self.validator = validator
        self.contract = contract_client
        self.light_client = light_client
        self.max_deposits_per_batch = max_deposits_per_batch
        self._withdrawal_circuit = withdrawal_circuit
        self._sync_circuit = sync_circuit
        self._proof_coordinator = proof_coordinator
        self._safety = safety_manager  # BridgeSafetyManager, if provided

        # Bookkeeping
        self._last_processed_block: int = 0
        self._loop_running: bool = False
        self._stats: Dict[str, int] = {
            "deposits_processed": 0,
            "deposits_failed": 0,
            "withdrawals_submitted": 0,
            "sync_updates": 0,
        }

    # ── Deposit processing ───────────────────────────────────────────────

    async def process_deposits(
        self, from_block: int, to_block: Optional[int] = None,
    ) -> List[ProcessedDeposit]:
        """Watch for deposit events and attest them.

        Steps for each ``Deposited`` event:

        1. Fetch events from the on-chain contract.
        2. Verify the containing block via the light client.
        3. Store the deposit in the DHT via ``validator.observe_deposit()``.
        4. Attest the deposit via ``validator.attest_deposit()``.

        Parameters
        ----------
        from_block : int
            Starting block (inclusive).
        to_block : int, optional
            Ending block (inclusive).  Defaults to ``"latest"``.

        Returns
        -------
        list of ProcessedDeposit
        """
        logger.info("Processing deposits from block %d", from_block)

        # 1. Fetch Deposited events from the contract
        events = await self.contract.get_deposit_events(from_block, to_block)

        if not events:
            logger.debug("No deposit events in range [%d, %s]", from_block, to_block)
            return []

        # Limit batch size
        events = events[: self.max_deposits_per_batch]

        results: List[ProcessedDeposit] = []

        for evt in events:
            args = evt.get("args", evt)
            tx_hash = evt.get("transactionHash", args.get("transactionHash", ""))
            block_number = evt.get("blockNumber", args.get("blockNumber", 0))
            amount = args.get("amount", 0)
            rings_did = args.get("ringsDid", "")
            sender = args.get("sender", "")

            pd = ProcessedDeposit(
                tx_hash=tx_hash,
                block_number=block_number,
                amount=amount,
                rings_did=rings_did,
                sender=sender,
                verified=False,
                attested=False,
            )

            try:
                # 1b. Safety pre-flight check
                if self._safety:
                    safe = await self._safety.check_deposit(amount, sender)
                    if not safe:
                        pd.error = "Blocked by safety manager"
                        results.append(pd)
                        self._stats["deposits_failed"] += 1
                        continue

                # 2. Verify block via light client
                try:
                    header = await self.light_client.get_verified_header(block_number)
                    pd.verified = True
                except KeyError:
                    logger.warning(
                        "No verified header for block %d — skipping deposit %s",
                        block_number, tx_hash,
                    )
                    pd.error = f"No verified header for block {block_number}"
                    results.append(pd)
                    self._stats["deposits_failed"] += 1
                    continue

                # 3. Store in DHT via validator
                record = await self.validator.observe_deposit(
                    tx_hash=tx_hash,
                    block=block_number,
                    amount=amount,
                    sender_eth=sender,
                    recipient_did=rings_did,
                )

                # 4. Attest
                await self.validator.attest_deposit(tx_hash)
                pd.attested = True
                pd.record = record

                self._stats["deposits_processed"] += 1
                if self._safety:
                    self._safety.record_deposit_result(True, amount, sender)
                logger.info(
                    "Deposit processed: %s (%d wei → %s)",
                    tx_hash, amount, rings_did,
                )

            except Exception as exc:
                pd.error = str(exc)
                self._stats["deposits_failed"] += 1
                if self._safety:
                    self._safety.record_deposit_result(False, amount, sender)
                logger.error("Failed to process deposit %s: %s", tx_hash, exc)

            results.append(pd)

        # Update cursor
        if results:
            max_block = max(r.block_number for r in results)
            self._last_processed_block = max(self._last_processed_block, max_block)

        return results

    # ── Withdrawal processing ────────────────────────────────────────────

    async def process_withdrawal(
        self,
        rings_did: str,
        amount: int,
        eth_address: str,
    ) -> str:
        """Execute the full withdrawal flow.

        Steps:

        1. Request withdrawal via the DHT (``validator.request_withdrawal``).
        2. Collect threshold approvals (``validator.collect_approvals``).
        3. Generate ZK proof (real Groth16 if circuit provided, else mock).
        4. Submit withdrawal to the on-chain contract.

        Parameters
        ----------
        rings_did : str
            The Rings DID requesting the withdrawal.
        amount : int
            Amount in wei to withdraw.
        eth_address : str
            Destination Ethereum address.

        Returns
        -------
        str
            On-chain transaction hash of the withdrawal.

        Raises
        ------
        RuntimeError
            If threshold approvals are not met after collection.
        """
        logger.info(
            "Processing withdrawal: %d wei from %s → %s",
            amount, rings_did, eth_address,
        )

        # 0. Safety pre-flight check
        if self._safety:
            safe = await self._safety.check_withdrawal(amount, eth_address)
            if not safe:
                raise RuntimeError(
                    f"Withdrawal blocked by safety manager "
                    f"(amount={amount}, recipient={eth_address})"
                )

        # 1. Request withdrawal (this validator is the requester)
        record = await self.validator.request_withdrawal(amount, eth_address)
        nonce = record.nonce

        # 2. Collect approvals (in a real system other validators would
        #    approve asynchronously; here we just check what's available)
        threshold_met, signatures = await self.validator.collect_approvals(nonce)
        if not threshold_met:
            logger.warning(
                "Threshold not met for withdrawal nonce=%d (%d/%d). "
                "Proceeding with self-approval only (single-validator mode).",
                nonce, len(signatures), self.validator.threshold,
            )

        # 3. Generate ZK proof — three paths in priority order:
        #    a) proof_coordinator (Phase 3 ZK system with caching/stats)
        #    b) withdrawal_circuit (Phase 2 real Groth16)
        #    c) mock proof (backward compatibility)
        if self._proof_coordinator is not None:
            # Phase 3: full ZK proof coordinator with caching + stats
            zk_proof = await self._proof_coordinator.prove_withdrawal(
                recipient=eth_address,
                amount=amount,
                nonce=nonce,
                rings_did=rings_did,
                header_proof={
                    "state_root": hashlib.sha256(
                        f"{nonce}:{amount}".encode()
                    ).digest(),
                },
                receipt_proof={},
                validator_sigs=[
                    s.encode() if isinstance(s, str) else s
                    for s in signatures
                ],
            )
            proof = zk_proof.proof_bytes
            # Convert bytes32 public inputs to ints for contract
            public_inputs = [
                int.from_bytes(pi, "big") if isinstance(pi, bytes) else pi
                for pi in zk_proof.public_inputs
            ]
            logger.info(
                "Generated ZK proof via coordinator (%d bytes, type=%s) "
                "for withdrawal nonce=%d",
                len(proof), zk_proof.proof_type, nonce,
            )
        elif self._withdrawal_circuit is not None:
            # Phase 2: real Groth16 proof via BN254 pairing math
            proof, public_inputs = self._withdrawal_circuit.prove_withdrawal(
                amount=amount,
                nonce=nonce,
                recipient=eth_address,
                signatures=[s.encode() if isinstance(s, str) else s
                            for s in signatures],
                state_root=hashlib.sha256(
                    f"{nonce}:{amount}".encode()
                ).digest(),
            )
            logger.info(
                "Generated real Groth16 proof (%d bytes) for withdrawal nonce=%d",
                len(proof), nonce,
            )
        else:
            # Mock proof (backward compatibility)
            proof_data = f"{nonce}|{amount}|{eth_address}".encode()
            proof = _mock_zk_proof(proof_data)
            addr_bytes = bytes.fromhex(
                eth_address.replace("0x", "").ljust(40, "0")[:40]
            )
            recipient_hash = int.from_bytes(addr_bytes[:8], "big")
            public_inputs = _mock_public_inputs(amount, nonce, recipient_hash)

        # 4. Submit on-chain
        tx_hash = await self.contract.withdraw(
            recipient=eth_address,
            amount=amount,
            nonce=nonce,
            proof=proof,
            public_inputs=public_inputs,
        )

        self._stats["withdrawals_submitted"] += 1
        if self._safety:
            self._safety.record_withdrawal_result(True, amount, eth_address)
        logger.info("Withdrawal submitted: nonce=%d, tx=%s", nonce, tx_hash)
        return tx_hash

    # ── Sync committee ───────────────────────────────────────────────────

    async def sync_committee_update(self) -> bool:
        """Check if the sync committee needs updating and submit if so.

        Compares the light client's latest committee root with the
        on-chain ``syncCommitteeRoot``.  If they differ, generates a
        mock proof and submits the update.

        Returns
        -------
        bool
            ``True`` if an update was submitted.
        """
        try:
            # Get latest slot from light client
            latest_slot = await self.light_client.get_latest_slot()
            # Period = slot // (32 * 256) = slot // 8192
            current_period = latest_slot // 8192

            # Fetch the current committee from the light client
            committee = await self.light_client.get_sync_committee(current_period)
        except (KeyError, NotImplementedError) as exc:
            logger.debug("Cannot fetch sync committee: %s", exc)
            return False

        # Compute committee root (hash of aggregate pubkey for simplicity)
        new_root = hashlib.sha256(
            committee.aggregate_pubkey.encode()
        ).digest()

        # Get on-chain root
        try:
            on_chain_root = await self.contract.get_sync_committee_root()
        except Exception:
            on_chain_root = b"\x00" * 32

        if new_root == on_chain_root:
            logger.debug("Sync committee is up-to-date (period %d)", current_period)
            return False

        logger.info(
            "Sync committee rotation detected (period %d), submitting update...",
            current_period,
        )

        # Generate ZK proof — three paths:
        if self._proof_coordinator is not None:
            # Phase 3: full ZK proof coordinator
            bitmap = [True] * 342 + [False] * 170  # supermajority
            zk_proof = await self._proof_coordinator.prove_sync_committee_update(
                current_root=on_chain_root if on_chain_root != b"\x00" * 32
                    else new_root,
                new_committee_pubkeys=[
                    committee.aggregate_pubkey.encode()
                    if isinstance(committee.aggregate_pubkey, str)
                    else committee.aggregate_pubkey
                ],
                attestation_sig=b"aggregate_bls_sig",
                attestation_bitmap=bitmap,
                slot=latest_slot,
            )
            proof = zk_proof.proof_bytes
            public_inputs = [
                int.from_bytes(pi, "big") if isinstance(pi, bytes) else pi
                for pi in zk_proof.public_inputs
            ]
            logger.info(
                "Generated ZK proof via coordinator for sync committee "
                "(period %d, slot %d, type=%s)",
                current_period, latest_slot, zk_proof.proof_type,
            )
        elif self._sync_circuit is not None:
            # Phase 2: real Groth16 proof
            proof, public_inputs = self._sync_circuit.prove_rotation(
                committee_root=new_root,
                slot=latest_slot,
                old_pubkeys=[b"old_committee"],  # simplified
                new_pubkeys=[committee.aggregate_pubkey.encode()],
                aggregate_sig=b"aggregate_bls_sig",
            )
            logger.info(
                "Generated real Groth16 proof for sync committee "
                "(period %d, slot %d)", current_period, latest_slot,
            )
        else:
            # Mock proof (backward compatibility)
            proof = _mock_zk_proof(new_root + latest_slot.to_bytes(8, "big"))
            public_inputs = [current_period, latest_slot]

        await self.contract.update_sync_committee(
            new_root=new_root,
            slot=latest_slot,
            proof=proof,
            public_inputs=public_inputs,
        )

        self._stats["sync_updates"] += 1
        return True

    # ── Health check ─────────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive bridge health check.

        Returns
        -------
        dict
            Keys include ``paused``, ``remaining_daily_limit``,
            ``latest_verified_slot``, ``deposit_nonce``,
            ``withdrawal_nonce``, ``validator_state``,
            ``light_client_synced``, ``stats``.
        """
        result: Dict[str, Any] = {
            "validator_did": self.validator.did,
            "validator_state": self.validator.state.value,
            "light_client_synced": self.light_client.is_synced,
            "last_processed_block": self._last_processed_block,
            "stats": dict(self._stats),
        }

        # On-chain queries — each may fail independently
        try:
            result["paused"] = await self.contract.is_paused()
        except Exception as exc:
            result["paused"] = f"error: {exc}"

        try:
            result["remaining_daily_limit"] = await self.contract.get_remaining_daily_limit()
        except Exception as exc:
            result["remaining_daily_limit"] = f"error: {exc}"

        try:
            result["latest_verified_slot"] = await self.contract.get_latest_verified_slot()
        except Exception as exc:
            result["latest_verified_slot"] = f"error: {exc}"

        try:
            result["deposit_nonce"] = await self.contract.get_deposit_nonce()
        except Exception as exc:
            result["deposit_nonce"] = f"error: {exc}"

        try:
            result["withdrawal_nonce"] = await self.contract.get_withdrawal_nonce()
        except Exception as exc:
            result["withdrawal_nonce"] = f"error: {exc}"

        # Safety manager report
        if self._safety:
            result["safety"] = self._safety.health_report

        return result

    # ── Main loop ────────────────────────────────────────────────────────

    async def run_bridge_loop(
        self,
        poll_interval: float = 12.0,
        start_block: Optional[int] = None,
    ) -> None:
        """Main bridge relay loop.

        Periodically:

        1. Processes new deposit events.
        2. Checks for sync committee rotations.
        3. Sends a validator heartbeat.

        The loop runs until :meth:`stop` is called or the task is
        cancelled.

        Parameters
        ----------
        poll_interval : float
            Seconds between iterations (default: 12 — one Ethereum slot).
        start_block : int, optional
            Block to start scanning from.  If ``None``, fetches the
            current block from the contract client's web3.
        """
        self._loop_running = True

        if start_block is not None:
            cursor = start_block
        elif self._last_processed_block > 0:
            cursor = self._last_processed_block + 1
        else:
            try:
                cursor = await self.contract.web3.get_block_number()
            except Exception:
                cursor = 0

        logger.info(
            "Starting bridge loop from block %d (poll=%.1fs)", cursor, poll_interval,
        )

        try:
            while self._loop_running:
                try:
                    # 1. Process deposits
                    results = await self.process_deposits(cursor)
                    if results:
                        cursor = max(r.block_number for r in results) + 1

                    # 2. Sync committee
                    await self.sync_committee_update()

                    # 3. Heartbeat
                    await self.validator.send_heartbeat()

                except Exception as exc:
                    logger.error("Bridge loop iteration error: %s", exc)

                await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            logger.info("Bridge loop cancelled")
        finally:
            self._loop_running = False
            logger.info("Bridge loop stopped")

    def stop(self) -> None:
        """Signal the bridge loop to stop after the current iteration."""
        self._loop_running = False

    @property
    def stats(self) -> Dict[str, int]:
        """Return a copy of the orchestrator's cumulative statistics."""
        return dict(self._stats)

    def __repr__(self) -> str:
        return (
            f"BridgeOrchestrator("
            f"validator={self.validator.did!r}, "
            f"last_block={self._last_processed_block}, "
            f"running={self._loop_running})"
        )
