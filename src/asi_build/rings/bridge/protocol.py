"""
Bridge Sub-Ring Protocol
=========================

Defines the DHT key schema and message types for the Rings ↔ Ethereum
bridge Sub-Ring.  Validators in the bridge Sub-Ring cooperate to:

1. **Observe** Ethereum deposit events (via light client).
2. **Attest** that a deposit is genuine (threshold signatures).
3. **Approve** withdrawal requests (multisig).
4. **Relay** committee updates for sync-committee rotation.

The bridge uses a *t-of-n* threshold scheme — a configurable quorum of
validators must attest a deposit or approve a withdrawal before it is
considered final.

Key Schema
~~~~~~~~~~

All bridge state lives in the Chord DHT under deterministic keys::

    bridge:eth:header:{block}       — verified Beacon header
    bridge:eth:committee:{period}   — sync committee for period
    bridge:eth:state:{addr}:{block} — EIP-1186 state proof
    bridge:deposit:{tx_hash}        — deposit record + attestations
    bridge:withdrawal:{nonce}       — withdrawal record + approvals
    bridge:validator:{did}          — validator heartbeat / metadata

Message Types
~~~~~~~~~~~~~

Messages are broadcast within the ``asi-build:bridge`` Sub-Ring::

    DEPOSIT_OBSERVED   — a new deposit was seen on Ethereum
    DEPOSIT_ATTESTED   — a validator attests the deposit
    WITHDRAWAL_REQUEST — a Rings user requests a withdrawal
    WITHDRAWAL_APPROVED — a validator approves the withdrawal
    COMMITTEE_UPDATE   — new Ethereum sync committee detected
    HEARTBEAT          — periodic liveness ping
    EMERGENCY_HALT     — circuit-breaker activation
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BridgeState(enum.Enum):
    """Lifecycle states for the bridge validator."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    HALTED = "halted"  # Emergency stop — all operations frozen


class BridgeMessage(enum.Enum):
    """Message types broadcast within the bridge Sub-Ring."""

    DEPOSIT_OBSERVED = "deposit_observed"
    DEPOSIT_ATTESTED = "deposit_attested"
    WITHDRAWAL_REQUEST = "withdrawal_request"
    WITHDRAWAL_APPROVED = "withdrawal_approved"
    COMMITTEE_UPDATE = "committee_update"
    HEARTBEAT = "heartbeat"
    EMERGENCY_HALT = "emergency_halt"


# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------


@dataclass
class DepositRecord:
    """A pending or finalized deposit from Ethereum into Rings.

    Attributes
    ----------
    tx_hash : str
        The Ethereum transaction hash of the deposit.
    block_number : int
        Block in which the deposit was mined.
    amount : int
        Deposit amount in wei.
    sender_eth : str
        The ``0x``-prefixed Ethereum address of the depositor.
    recipient_did : str
        The Rings DID that should be credited.
    timestamp : float
        Unix timestamp when the deposit was first observed.
    attestations : dict
        Map of ``validator_did → signature``.  Once the attestation
        count reaches the threshold the deposit is considered finalized.
    finalized : bool
        Whether the deposit has been finalized (threshold met).
    """

    tx_hash: str
    block_number: int
    amount: int  # in wei
    sender_eth: str  # Ethereum 0x address
    recipient_did: str  # Rings DID
    timestamp: float = field(default_factory=time.time)
    attestations: Dict[str, bytes] = field(default_factory=dict)  # did → signature
    finalized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for DHT storage (bytes → hex strings)."""
        return {
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "amount": self.amount,
            "sender_eth": self.sender_eth,
            "recipient_did": self.recipient_did,
            "timestamp": self.timestamp,
            "attestations": {
                did: sig.hex() if isinstance(sig, bytes) else sig
                for did, sig in self.attestations.items()
            },
            "finalized": self.finalized,
        }


@dataclass
class WithdrawalRecord:
    """A pending or executed withdrawal from Rings to Ethereum.

    Attributes
    ----------
    nonce : int
        Monotonically increasing withdrawal sequence number.
    amount : int
        Withdrawal amount in wei.
    requester_did : str
        The Rings DID requesting the withdrawal.
    recipient_eth : str
        The ``0x``-prefixed Ethereum address to send to.
    timestamp : float
        Unix timestamp when the withdrawal was requested.
    approvals : dict
        Map of ``validator_did → signature``.
    executed : bool
        Whether the withdrawal has been executed on Ethereum.
    """

    nonce: int
    amount: int  # in wei
    requester_did: str
    recipient_eth: str  # Ethereum 0x address
    timestamp: float = field(default_factory=time.time)
    approvals: Dict[str, bytes] = field(default_factory=dict)  # did → signature
    executed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for DHT storage (bytes → hex strings)."""
        return {
            "nonce": self.nonce,
            "amount": self.amount,
            "requester_did": self.requester_did,
            "recipient_eth": self.recipient_eth,
            "timestamp": self.timestamp,
            "approvals": {
                did: sig.hex() if isinstance(sig, bytes) else sig
                for did, sig in self.approvals.items()
            },
            "executed": self.executed,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sig_dict(raw: Dict[str, Any]) -> Dict[str, bytes]:
    """Parse a dict of ``{did: hex_or_bytes}`` into ``{did: bytes}``."""
    result: Dict[str, bytes] = {}
    for did, sig in raw.items():
        if isinstance(sig, str):
            result[did] = bytes.fromhex(sig)
        elif isinstance(sig, bytes):
            result[did] = sig
    return result


# ---------------------------------------------------------------------------
# BridgeProtocol — static DHT key schema & message encoding
# ---------------------------------------------------------------------------


class BridgeProtocol:
    """Static methods for DHT key schema used by the bridge Sub-Ring.

    All bridge-related data is stored in the Chord DHT under a
    deterministic key namespace so any validator can locate it.
    """

    BRIDGE_SUBRING = "asi-build:bridge"

    # ── DHT key constructors ─────────────────────────────────────────────

    @staticmethod
    def eth_header_key(block_number: int) -> str:
        """DHT key for a verified Ethereum Beacon header.

        >>> BridgeProtocol.eth_header_key(123456)
        'bridge:eth:header:123456'
        """
        return f"bridge:eth:header:{block_number}"

    @staticmethod
    def eth_sync_committee_key(period: int) -> str:
        """DHT key for a sync committee snapshot.

        >>> BridgeProtocol.eth_sync_committee_key(800)
        'bridge:eth:committee:800'
        """
        return f"bridge:eth:committee:{period}"

    @staticmethod
    def eth_state_proof_key(address: str, block: int) -> str:
        """DHT key for an Ethereum state proof (EIP-1186).

        >>> BridgeProtocol.eth_state_proof_key('0xabc', 100)
        'bridge:eth:state:0xabc:100'
        """
        return f"bridge:eth:state:{address}:{block}"

    @staticmethod
    def bridge_deposit_key(tx_hash: str) -> str:
        """DHT key for a deposit record.

        >>> BridgeProtocol.bridge_deposit_key('0xdeadbeef')
        'bridge:deposit:0xdeadbeef'
        """
        return f"bridge:deposit:{tx_hash}"

    @staticmethod
    def bridge_withdrawal_key(nonce: int) -> str:
        """DHT key for a withdrawal record.

        >>> BridgeProtocol.bridge_withdrawal_key(42)
        'bridge:withdrawal:42'
        """
        return f"bridge:withdrawal:{nonce}"

    @staticmethod
    def bridge_validator_key(did: str) -> str:
        """DHT key for a validator's heartbeat / metadata.

        >>> BridgeProtocol.bridge_validator_key('did:rings:ed25519:abc')
        'bridge:validator:did:rings:ed25519:abc'
        """
        return f"bridge:validator:{did}"

    # ── Message encoding ─────────────────────────────────────────────────

    @staticmethod
    def encode_message(msg_type: BridgeMessage, payload: dict) -> dict:
        """Encode a bridge message for Sub-Ring broadcast.

        Parameters
        ----------
        msg_type : BridgeMessage
            The message type.
        payload : dict
            Message-specific data.

        Returns
        -------
        dict
            A JSON-serializable envelope with ``type``, ``payload``, and
            ``timestamp`` fields.
        """
        return {
            "type": msg_type.value,
            "payload": payload,
            "timestamp": time.time(),
        }

    @staticmethod
    def decode_message(raw: dict) -> Tuple[BridgeMessage, dict]:
        """Decode a bridge message from a Sub-Ring broadcast.

        Parameters
        ----------
        raw : dict
            The raw message envelope.

        Returns
        -------
        tuple of (BridgeMessage, dict)
            The decoded message type and its payload.

        Raises
        ------
        ValueError
            If the message type is unknown.
        KeyError
            If required fields are missing.
        """
        type_str = raw["type"]
        payload = raw.get("payload", {})
        try:
            msg_type = BridgeMessage(type_str)
        except ValueError:
            raise ValueError(f"Unknown bridge message type: {type_str!r}")
        return msg_type, payload


# ---------------------------------------------------------------------------
# BridgeValidator — validator node logic
# ---------------------------------------------------------------------------


class BridgeValidator:
    """A bridge validator node that participates in the bridge Sub-Ring.

    The validator observes Ethereum deposits, attests their validity via
    threshold signatures, and approves withdrawal requests.

    Parameters
    ----------
    identity : object
        Any object with ``sign_rings(data: bytes) -> bytes`` and a
        ``rings_did: str`` attribute (duck-typed).
    client : RingsClient
        A connected :class:`~asi_build.rings.client.RingsClient`.
    threshold : int
        Minimum number of attestations/approvals required.
    total : int
        Expected total number of validators.
    """

    def __init__(
        self,
        identity: Any,
        client: Any,
        *,
        threshold: int = 4,
        total: int = 6,
    ) -> None:
        self.identity = identity
        self.client = client
        self.threshold = threshold
        self.total = total
        self.state = BridgeState.INITIALIZING
        self.deposits: Dict[str, DepositRecord] = {}
        self.withdrawals: Dict[int, WithdrawalRecord] = {}
        self._withdrawal_nonce = 0

    @property
    def did(self) -> str:
        """The DID of this validator."""
        return self.identity.rings_did

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def join_bridge(self) -> None:
        """Join the bridge Sub-Ring and register as a validator.

        1. Joins the ``asi-build:bridge`` Sub-Ring.
        2. Publishes a validator registration record to the DHT.
        3. Transitions to ``ACTIVE`` state.
        """
        await self.client.join_sub_ring(BridgeProtocol.BRIDGE_SUBRING)

        # Register in DHT
        key = BridgeProtocol.bridge_validator_key(self.did)
        await self.client.dht_put(key, {
            "did": self.did,
            "state": BridgeState.ACTIVE.value,
            "joined_at": time.time(),
            "threshold": self.threshold,
            "total": self.total,
        })

        self.state = BridgeState.ACTIVE
        logger.info("Validator %s joined bridge Sub-Ring", self.did)

    # ── Internal: DHT read-modify-write helpers ──────────────────────────

    async def _fetch_deposit(self, tx_hash: str) -> DepositRecord:
        """Fetch a deposit record, merging local state with DHT.

        Always reads from DHT to pick up attestations from other
        validators, then merges with any local attestations.

        Raises
        ------
        KeyError
            If the deposit is not found locally or in the DHT.
        """
        dht_key = BridgeProtocol.bridge_deposit_key(tx_hash)
        raw = await self.client.dht_get(dht_key)

        local = self.deposits.get(tx_hash)

        if raw is None and local is None:
            raise KeyError(f"Unknown deposit: {tx_hash}")

        if raw is not None:
            # Build record from DHT data
            dht_attestations = _parse_sig_dict(raw.get("attestations", {}))
            record = DepositRecord(
                tx_hash=raw["tx_hash"],
                block_number=raw["block_number"],
                amount=raw["amount"],
                sender_eth=raw["sender_eth"],
                recipient_did=raw["recipient_did"],
                timestamp=raw.get("timestamp", time.time()),
                attestations=dht_attestations,
                finalized=raw.get("finalized", False),
            )
            # Merge any local attestations not yet in DHT
            if local is not None:
                for did, sig in local.attestations.items():
                    if did not in record.attestations:
                        record.attestations[did] = sig
        else:
            # Only have local record
            record = local  # type: ignore[assignment]

        self.deposits[tx_hash] = record
        return record

    async def _fetch_withdrawal(self, nonce: int) -> WithdrawalRecord:
        """Fetch a withdrawal record, merging local state with DHT.

        Always reads from DHT to pick up approvals from other
        validators, then merges with any local approvals.

        Raises
        ------
        KeyError
            If the withdrawal is not found locally or in the DHT.
        """
        dht_key = BridgeProtocol.bridge_withdrawal_key(nonce)
        raw = await self.client.dht_get(dht_key)

        local = self.withdrawals.get(nonce)

        if raw is None and local is None:
            raise KeyError(f"Unknown withdrawal: nonce={nonce}")

        if raw is not None:
            dht_approvals = _parse_sig_dict(raw.get("approvals", {}))
            record = WithdrawalRecord(
                nonce=raw["nonce"],
                amount=raw["amount"],
                requester_did=raw["requester_did"],
                recipient_eth=raw["recipient_eth"],
                timestamp=raw.get("timestamp", time.time()),
                approvals=dht_approvals,
                executed=raw.get("executed", False),
            )
            # Merge local approvals
            if local is not None:
                for did, sig in local.approvals.items():
                    if did not in record.approvals:
                        record.approvals[did] = sig
        else:
            record = local  # type: ignore[assignment]

        self.withdrawals[nonce] = record
        return record

    # ── Deposit flow ─────────────────────────────────────────────────────

    async def observe_deposit(
        self,
        tx_hash: str,
        block: int,
        amount: int,
        sender_eth: str,
        recipient_did: str,
    ) -> DepositRecord:
        """Record a new deposit observed on Ethereum.

        Stores the deposit locally and publishes it to the DHT, then
        broadcasts a ``DEPOSIT_OBSERVED`` message to the Sub-Ring.

        Parameters
        ----------
        tx_hash : str
            Ethereum transaction hash.
        block : int
            Block number where the deposit was mined.
        amount : int
            Deposit amount in wei.
        sender_eth : str
            Depositor's Ethereum address.
        recipient_did : str
            Intended recipient's Rings DID.

        Returns
        -------
        DepositRecord
        """
        if self.state == BridgeState.HALTED:
            raise RuntimeError("Bridge is halted — cannot observe deposits")

        record = DepositRecord(
            tx_hash=tx_hash,
            block_number=block,
            amount=amount,
            sender_eth=sender_eth,
            recipient_did=recipient_did,
        )
        self.deposits[tx_hash] = record

        # Publish to DHT
        key = BridgeProtocol.bridge_deposit_key(tx_hash)
        await self.client.dht_put(key, record.to_dict())

        # Broadcast to Sub-Ring
        msg = BridgeProtocol.encode_message(
            BridgeMessage.DEPOSIT_OBSERVED,
            {"tx_hash": tx_hash, "block": block, "amount": amount,
             "sender_eth": sender_eth, "recipient_did": recipient_did},
        )
        await self.client.broadcast(BridgeProtocol.BRIDGE_SUBRING, msg)

        logger.info("Deposit observed: %s (%d wei)", tx_hash, amount)
        return record

    async def attest_deposit(self, tx_hash: str) -> bytes:
        """Attest that a deposit is valid by signing its content hash.

        The signature covers ``sha256(tx_hash | block | amount | recipient)``.

        Before signing, the current DHT record is fetched and merged with
        local state so that attestations from other validators are preserved
        in the write-back.

        Parameters
        ----------
        tx_hash : str
            The transaction hash of the deposit to attest.

        Returns
        -------
        bytes
            The attestation signature.

        Raises
        ------
        KeyError
            If the deposit is unknown (must be observed first or
            fetched from DHT).
        RuntimeError
            If the bridge is halted.
        """
        if self.state == BridgeState.HALTED:
            raise RuntimeError("Bridge is halted — cannot attest deposits")

        # Fetch from DHT + merge with local (picks up other validators' attestations)
        record = await self._fetch_deposit(tx_hash)

        # Sign: H(tx_hash | block | amount | recipient)
        data = (
            f"{record.tx_hash}|{record.block_number}|"
            f"{record.amount}|{record.recipient_did}"
        ).encode()
        digest = hashlib.sha256(data).digest()
        signature = self.identity.sign_rings(digest)

        # Store attestation locally + in merged record
        record.attestations[self.did] = signature

        # Write back to DHT (includes all known attestations)
        key = BridgeProtocol.bridge_deposit_key(tx_hash)
        await self.client.dht_put(key, record.to_dict())

        # Broadcast attestation
        msg = BridgeProtocol.encode_message(
            BridgeMessage.DEPOSIT_ATTESTED,
            {"tx_hash": tx_hash, "validator": self.did,
             "signature": signature.hex()},
        )
        await self.client.broadcast(BridgeProtocol.BRIDGE_SUBRING, msg)

        logger.info("Deposit attested: %s by %s", tx_hash, self.did)
        return signature

    async def collect_attestations(self, tx_hash: str) -> Tuple[bool, List[bytes]]:
        """Collect attestations for a deposit from the DHT.

        Checks if the threshold has been met. If so, marks the deposit
        as finalized.

        Parameters
        ----------
        tx_hash : str
            The transaction hash to check.

        Returns
        -------
        tuple of (bool, list of bytes)
            ``(threshold_met, list_of_signatures)``.
        """
        # Refresh from DHT
        raw = await self.client.dht_get(
            BridgeProtocol.bridge_deposit_key(tx_hash)
        )
        if raw is None:
            return False, []

        attestations = _parse_sig_dict(raw.get("attestations", {}))
        signatures = list(attestations.values())

        # Update local record
        record = self.deposits.get(tx_hash)
        if record is not None:
            record.attestations.update(attestations)

        threshold_met = len(signatures) >= self.threshold

        if threshold_met and record is not None and not record.finalized:
            record.finalized = True
            await self.client.dht_put(
                BridgeProtocol.bridge_deposit_key(tx_hash),
                record.to_dict(),
            )
            logger.info(
                "Deposit finalized: %s (%d/%d attestations)",
                tx_hash, len(signatures), self.threshold,
            )

        return threshold_met, signatures

    # ── Withdrawal flow ──────────────────────────────────────────────────

    async def request_withdrawal(
        self, amount: int, eth_address: str
    ) -> WithdrawalRecord:
        """Create a new withdrawal request.

        The requester is this validator's DID. A ``WITHDRAWAL_REQUEST``
        message is broadcast to the Sub-Ring for other validators to
        approve.

        Parameters
        ----------
        amount : int
            Withdrawal amount in wei.
        eth_address : str
            Destination Ethereum address.

        Returns
        -------
        WithdrawalRecord
        """
        if self.state == BridgeState.HALTED:
            raise RuntimeError("Bridge is halted — cannot request withdrawals")

        nonce = self._withdrawal_nonce
        self._withdrawal_nonce += 1

        record = WithdrawalRecord(
            nonce=nonce,
            amount=amount,
            requester_did=self.did,
            recipient_eth=eth_address,
        )
        self.withdrawals[nonce] = record

        # Publish to DHT
        key = BridgeProtocol.bridge_withdrawal_key(nonce)
        await self.client.dht_put(key, record.to_dict())

        # Broadcast
        msg = BridgeProtocol.encode_message(
            BridgeMessage.WITHDRAWAL_REQUEST,
            {"nonce": nonce, "amount": amount, "eth_address": eth_address,
             "requester": self.did},
        )
        await self.client.broadcast(BridgeProtocol.BRIDGE_SUBRING, msg)

        logger.info("Withdrawal requested: nonce=%d, %d wei → %s",
                     nonce, amount, eth_address)
        return record

    async def approve_withdrawal(self, nonce: int) -> bytes:
        """Approve a withdrawal request by signing it.

        The signature covers ``sha256(nonce | amount | requester | recipient)``.

        Before signing, the current DHT record is fetched and merged with
        local state so that approvals from other validators are preserved
        in the write-back.

        Parameters
        ----------
        nonce : int
            The withdrawal nonce to approve.

        Returns
        -------
        bytes
            The approval signature.

        Raises
        ------
        KeyError
            If the withdrawal is unknown.
        RuntimeError
            If the bridge is halted.
        """
        if self.state == BridgeState.HALTED:
            raise RuntimeError("Bridge is halted — cannot approve withdrawals")

        # Fetch from DHT + merge with local (picks up other validators' approvals)
        record = await self._fetch_withdrawal(nonce)

        # Sign: H(nonce | amount | requester | recipient)
        data = (
            f"{record.nonce}|{record.amount}|"
            f"{record.requester_did}|{record.recipient_eth}"
        ).encode()
        digest = hashlib.sha256(data).digest()
        signature = self.identity.sign_rings(digest)

        # Store approval locally + in merged record
        record.approvals[self.did] = signature

        # Write back to DHT (includes all known approvals)
        key = BridgeProtocol.bridge_withdrawal_key(nonce)
        await self.client.dht_put(key, record.to_dict())

        # Broadcast
        msg = BridgeProtocol.encode_message(
            BridgeMessage.WITHDRAWAL_APPROVED,
            {"nonce": nonce, "validator": self.did,
             "signature": signature.hex()},
        )
        await self.client.broadcast(BridgeProtocol.BRIDGE_SUBRING, msg)

        logger.info("Withdrawal approved: nonce=%d by %s", nonce, self.did)
        return signature

    async def collect_approvals(self, nonce: int) -> Tuple[bool, List[bytes]]:
        """Collect approvals for a withdrawal from the DHT.

        Parameters
        ----------
        nonce : int
            The withdrawal nonce to check.

        Returns
        -------
        tuple of (bool, list of bytes)
            ``(threshold_met, list_of_signatures)``.
        """
        raw = await self.client.dht_get(
            BridgeProtocol.bridge_withdrawal_key(nonce)
        )
        if raw is None:
            return False, []

        approvals = _parse_sig_dict(raw.get("approvals", {}))
        signatures = list(approvals.values())

        # Update local record
        record = self.withdrawals.get(nonce)
        if record is not None:
            record.approvals.update(approvals)

        threshold_met = len(signatures) >= self.threshold

        if threshold_met and record is not None and not record.executed:
            record.executed = True
            await self.client.dht_put(
                BridgeProtocol.bridge_withdrawal_key(nonce),
                record.to_dict(),
            )
            logger.info(
                "Withdrawal executable: nonce=%d (%d/%d approvals)",
                nonce, len(signatures), self.threshold,
            )

        return threshold_met, signatures

    # ── Heartbeat & emergency ────────────────────────────────────────────

    async def send_heartbeat(self) -> None:
        """Broadcast a heartbeat to the bridge Sub-Ring.

        Also updates the validator's DHT record with the latest timestamp
        and state.
        """
        now = time.time()

        # Update DHT record
        key = BridgeProtocol.bridge_validator_key(self.did)
        await self.client.dht_put(key, {
            "did": self.did,
            "state": self.state.value,
            "last_heartbeat": now,
            "deposits_observed": len(self.deposits),
            "withdrawals_processed": len(self.withdrawals),
        })

        # Broadcast
        msg = BridgeProtocol.encode_message(
            BridgeMessage.HEARTBEAT,
            {"validator": self.did, "state": self.state.value},
        )
        await self.client.broadcast(BridgeProtocol.BRIDGE_SUBRING, msg)

    async def emergency_halt(self, reason: str) -> None:
        """Trigger an emergency halt of the bridge.

        Transitions to ``HALTED`` state and broadcasts an emergency halt
        message. All deposit/withdrawal operations will be refused.

        Parameters
        ----------
        reason : str
            Human-readable reason for the halt (e.g. "suspicious deposit
            pattern detected").
        """
        self.state = BridgeState.HALTED
        logger.critical("BRIDGE EMERGENCY HALT by %s: %s", self.did, reason)

        # Update DHT
        key = BridgeProtocol.bridge_validator_key(self.did)
        await self.client.dht_put(key, {
            "did": self.did,
            "state": BridgeState.HALTED.value,
            "halt_reason": reason,
            "halted_at": time.time(),
        })

        # Broadcast emergency halt
        msg = BridgeProtocol.encode_message(
            BridgeMessage.EMERGENCY_HALT,
            {"validator": self.did, "reason": reason},
        )
        await self.client.broadcast(BridgeProtocol.BRIDGE_SUBRING, msg)

    # ── Helpers ──────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"BridgeValidator(did={self.did!r}, state={self.state.value}, "
            f"deposits={len(self.deposits)}, withdrawals={len(self.withdrawals)}, "
            f"threshold={self.threshold}/{self.total})"
        )
