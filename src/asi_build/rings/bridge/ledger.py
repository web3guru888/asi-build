"""
Rings-Side Token Ledger
========================

DHT-backed token ledger with validator consensus for tracking bridged
token balances on the Rings P2P network.  Enables agent-to-agent payments
without going back through Ethereum.

Architecture
~~~~~~~~~~~~

Balances and transfer records are stored in the Chord DHT under
deterministic keys::

    rings:ledger:balance:{did}:{token}   → int (amount in wei)
    rings:ledger:tx:{transfer_id}        → TransferRecord (JSON)
    rings:ledger:history:{did}           → list of transfer_ids
    rings:ledger:lock:{did}:{token}      → int (locked for pending transfers)
    rings:ledger:nonce:{did}             → int (monotonic nonce per sender)

Validators also maintain a local SQLite mirror for consistency.

Transfer Lifecycle
~~~~~~~~~~~~~~~~~~

::

    PROPOSED   → sender signs transfer intent
    ATTESTING  → validators verify balance, sign attestations
    FINALIZED  → 4/6 threshold reached, balances updated atomically
    FAILED     → insufficient balance, timeout, or validator rejection
    EXPIRED    → attestation window elapsed without threshold

Consensus Model
~~~~~~~~~~~~~~~

Reuses the 4/6 threshold attestation pattern from
:class:`~.protocol.BridgeValidator`.  A transfer only finalizes when
≥ *threshold* validators attest that the sender has sufficient balance.
Pending transfers lock the amount to prevent double-spending.

Token Identifiers
~~~~~~~~~~~~~~~~~

Canonical token ID is the Ethereum contract address.  Special values:

- ``"ETH"`` or ``"0x0000000000000000000000000000000000000000"`` → native ETH
- ``"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"`` → USDC
- Any 0x-prefixed 42-char hex string → ERC-20 token

Bridge Integration
~~~~~~~~~~~~~~~~~~

The relayer calls :meth:`RingsTokenLedger.credit_from_bridge` after a
verified deposit, and :meth:`debit_for_withdrawal` when a user wants
to withdraw back to Ethereum.
"""

from __future__ import annotations

import asyncio
import enum
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default attestation threshold: 4 of 6 validators must agree.
DEFAULT_THRESHOLD: int = 4
DEFAULT_TOTAL: int = 6

#: How long (seconds) a transfer proposal stays open for attestation.
DEFAULT_TRANSFER_TTL: float = 300.0  # 5 minutes

#: Maximum transfer history entries stored per DID in the DHT.
MAX_HISTORY_PER_DID: int = 500

#: Canonical token for native ETH.
ETH_TOKEN = "ETH"
ETH_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

#: DHT key namespace for the ledger.
LEDGER_NS = "rings:ledger"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TransferStatus(enum.Enum):
    """Lifecycle states for a Rings-side transfer."""

    PROPOSED = "proposed"
    ATTESTING = "attesting"
    FINALIZED = "finalized"
    FAILED = "failed"
    EXPIRED = "expired"


class LedgerMessage(enum.Enum):
    """Message types broadcast within the bridge Sub-Ring for ledger ops."""

    TRANSFER_PROPOSED = "transfer_proposed"
    TRANSFER_ATTESTED = "transfer_attested"
    TRANSFER_FINALIZED = "transfer_finalized"
    TRANSFER_FAILED = "transfer_failed"
    BALANCE_CREDITED = "balance_credited"
    BALANCE_DEBITED = "balance_debited"


# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------


@dataclass
class TransferRecord:
    """A transfer between two DIDs on the Rings network.

    Attributes
    ----------
    transfer_id : str
        Unique identifier (UUID).
    from_did : str
        Sender's Rings DID.
    to_did : str
        Recipient's Rings DID.
    token : str
        Token identifier (ETH address or ``"ETH"``).
    amount : int
        Transfer amount in the token's smallest unit (wei, etc.).
    nonce : int
        Sender's monotonic nonce at the time of the transfer.
    signature : str
        Hex-encoded sender signature over the transfer intent.
    timestamp : float
        Unix timestamp of proposal creation.
    status : TransferStatus
        Current lifecycle state.
    attestations : dict
        Map of ``validator_did → signature_hex`` from validators who
        attested the transfer is valid (sender has funds).
    rejection_reasons : dict
        Map of ``validator_did → reason`` for any rejections.
    finalized_at : float
        Timestamp when transfer was finalized (0.0 if not yet).
    error : str
        Error message if the transfer failed.
    """

    transfer_id: str
    from_did: str
    to_did: str
    token: str
    amount: int
    nonce: int = 0
    signature: str = ""
    timestamp: float = field(default_factory=time.time)
    status: TransferStatus = TransferStatus.PROPOSED
    attestations: Dict[str, str] = field(default_factory=dict)
    rejection_reasons: Dict[str, str] = field(default_factory=dict)
    finalized_at: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for DHT storage / JSON transport."""
        return {
            "transfer_id": self.transfer_id,
            "from_did": self.from_did,
            "to_did": self.to_did,
            "token": self.token,
            "amount": self.amount,
            "nonce": self.nonce,
            "signature": self.signature,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "attestations": dict(self.attestations),
            "rejection_reasons": dict(self.rejection_reasons),
            "finalized_at": self.finalized_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransferRecord":
        """Reconstruct from a dict (e.g. decoded from DHT)."""
        return cls(
            transfer_id=data["transfer_id"],
            from_did=data["from_did"],
            to_did=data["to_did"],
            token=data["token"],
            amount=data["amount"],
            nonce=data.get("nonce", 0),
            signature=data.get("signature", ""),
            timestamp=data.get("timestamp", time.time()),
            status=TransferStatus(data.get("status", "proposed")),
            attestations=dict(data.get("attestations", {})),
            rejection_reasons=dict(data.get("rejection_reasons", {})),
            finalized_at=data.get("finalized_at", 0.0),
            error=data.get("error", ""),
        )


@dataclass
class TransferReceipt:
    """Returned to the caller after a transfer attempt.

    Attributes
    ----------
    transfer_id : str
        The transfer's unique identifier.
    status : TransferStatus
        Current status (PROPOSED, ATTESTING, FINALIZED, FAILED, EXPIRED).
    attestation_count : int
        Number of validator attestations collected so far.
    threshold : int
        Number of attestations needed for finalization.
    timestamp : float
        When the receipt was generated.
    error : str
        Error message if applicable.
    """

    transfer_id: str
    status: TransferStatus
    attestation_count: int = 0
    threshold: int = DEFAULT_THRESHOLD
    timestamp: float = field(default_factory=time.time)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transfer_id": self.transfer_id,
            "status": self.status.value,
            "attestation_count": self.attestation_count,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "error": self.error,
        }


@dataclass
class WithdrawalLock:
    """Represents tokens locked for a bridge withdrawal back to Ethereum.

    Attributes
    ----------
    lock_id : str
        Unique lock identifier.
    did : str
        The DID whose tokens are locked.
    token : str
        Token being withdrawn.
    amount : int
        Amount locked (in smallest unit).
    timestamp : float
        When the lock was created.
    released : bool
        Whether the lock has been released (after withdrawal completes
        or is cancelled).
    """

    lock_id: str
    did: str
    token: str
    amount: int
    timestamp: float = field(default_factory=time.time)
    released: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lock_id": self.lock_id,
            "did": self.did,
            "token": self.token,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "released": self.released,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WithdrawalLock":
        return cls(
            lock_id=data["lock_id"],
            did=data["did"],
            token=data["token"],
            amount=data["amount"],
            timestamp=data.get("timestamp", time.time()),
            released=data.get("released", False),
        )


# ---------------------------------------------------------------------------
# DHT Key Schema
# ---------------------------------------------------------------------------


class LedgerKeys:
    """Static methods for deterministic DHT key construction.

    All ledger state lives under the ``rings:ledger:`` namespace.
    """

    @staticmethod
    def balance_key(did: str, token: str) -> str:
        """DHT key for a DID's balance of a specific token.

        >>> LedgerKeys.balance_key('did:rings:secp256k1:abc', 'ETH')
        'rings:ledger:balance:did:rings:secp256k1:abc:ETH'
        """
        return f"{LEDGER_NS}:balance:{did}:{_normalize_token(token)}"

    @staticmethod
    def transfer_key(transfer_id: str) -> str:
        """DHT key for a transfer record.

        >>> LedgerKeys.transfer_key('tx-123')
        'rings:ledger:tx:tx-123'
        """
        return f"{LEDGER_NS}:tx:{transfer_id}"

    @staticmethod
    def history_key(did: str) -> str:
        """DHT key for a DID's transfer history (list of transfer_ids).

        >>> LedgerKeys.history_key('did:rings:secp256k1:abc')
        'rings:ledger:history:did:rings:secp256k1:abc'
        """
        return f"{LEDGER_NS}:history:{did}"

    @staticmethod
    def lock_key(did: str, token: str) -> str:
        """DHT key for the total locked amount for a DID+token.

        >>> LedgerKeys.lock_key('did:rings:secp256k1:abc', 'ETH')
        'rings:ledger:lock:did:rings:secp256k1:abc:ETH'
        """
        return f"{LEDGER_NS}:lock:{did}:{_normalize_token(token)}"

    @staticmethod
    def nonce_key(did: str) -> str:
        """DHT key for a DID's monotonic transfer nonce.

        >>> LedgerKeys.nonce_key('did:rings:secp256k1:abc')
        'rings:ledger:nonce:did:rings:secp256k1:abc'
        """
        return f"{LEDGER_NS}:nonce:{did}"

    @staticmethod
    def withdrawal_lock_key(lock_id: str) -> str:
        """DHT key for a specific withdrawal lock record.

        >>> LedgerKeys.withdrawal_lock_key('lock-456')
        'rings:ledger:wdlock:lock-456'
        """
        return f"{LEDGER_NS}:wdlock:{lock_id}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_token(token: str) -> str:
    """Normalize a token identifier.

    - ``"ETH"`` stays ``"ETH"``
    - Zero address becomes ``"ETH"``
    - Other addresses lowercased for consistency

    Parameters
    ----------
    token : str
        The raw token identifier.

    Returns
    -------
    str
        Normalized token string.
    """
    if token.upper() == "ETH" or token == ETH_ZERO_ADDRESS:
        return ETH_TOKEN
    # Lowercase hex addresses for consistency
    if token.startswith("0x") and len(token) == 42:
        return token.lower()
    return token


def _compute_transfer_digest(
    from_did: str,
    to_did: str,
    token: str,
    amount: int,
    nonce: int,
) -> bytes:
    """Compute the SHA-256 digest of a transfer intent.

    This is the message that the sender signs to authorize the transfer.
    Format: ``sha256(from_did|to_did|token|amount|nonce)``.

    Parameters
    ----------
    from_did, to_did, token : str
        Transfer participants and token.
    amount : int
        Transfer amount.
    nonce : int
        Sender's monotonic nonce.

    Returns
    -------
    bytes
        32-byte SHA-256 digest.
    """
    canonical = f"{from_did}|{to_did}|{_normalize_token(token)}|{amount}|{nonce}"
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def _compute_attestation_digest(transfer_id: str, from_did: str, amount: int) -> bytes:
    """Compute the SHA-256 digest validators sign when attesting a transfer.

    Format: ``sha256(transfer_id|from_did|amount)``.

    Parameters
    ----------
    transfer_id : str
        The transfer being attested.
    from_did : str
        The sender's DID.
    amount : int
        Transfer amount.

    Returns
    -------
    bytes
        32-byte SHA-256 digest.
    """
    canonical = f"{transfer_id}|{from_did}|{amount}"
    return hashlib.sha256(canonical.encode("utf-8")).digest()


# ---------------------------------------------------------------------------
# RingsTokenLedger
# ---------------------------------------------------------------------------


class RingsTokenLedger:
    """Tracks bridged token balances on the Rings DHT.

    Uses validator consensus (4/6 threshold) for transfer finalization.

    Parameters
    ----------
    client : object
        A :class:`~asi_build.rings.client.RingsClient` (or any object
        with ``dht_put``, ``dht_get``, ``broadcast`` async methods).
    identity : object, optional
        Any object with ``sign_rings(data: bytes) -> bytes`` and a
        ``rings_did: str`` attribute (duck-typed).  Required for
        validator attestation.
    threshold : int
        Minimum attestations needed to finalize a transfer (default 4).
    total : int
        Expected total validator count (default 6).
    transfer_ttl : float
        Seconds before a pending transfer expires (default 300).
    """

    BRIDGE_SUBRING = "asi-build:bridge"

    def __init__(
        self,
        client: Any,
        identity: Any = None,
        *,
        threshold: int = DEFAULT_THRESHOLD,
        total: int = DEFAULT_TOTAL,
        transfer_ttl: float = DEFAULT_TRANSFER_TTL,
    ) -> None:
        if threshold > total:
            raise ValueError(
                f"threshold ({threshold}) cannot exceed total ({total})"
            )
        if threshold < 1:
            raise ValueError("threshold must be ≥ 1")

        self.client = client
        self.identity = identity
        self.threshold = threshold
        self.total = total
        self.transfer_ttl = transfer_ttl

        # Local mirrors for fast access (also written to DHT)
        self._balances: Dict[str, Dict[str, int]] = {}  # did → {token → amount}
        self._locks: Dict[str, Dict[str, int]] = {}     # did → {token → locked}
        self._transfers: Dict[str, TransferRecord] = {}  # transfer_id → record
        self._nonces: Dict[str, int] = {}                # did → next nonce
        self._withdrawal_locks: Dict[str, WithdrawalLock] = {}  # lock_id → lock
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = {
            "transfers_proposed": 0,
            "transfers_finalized": 0,
            "transfers_failed": 0,
            "credits": 0,
            "debits": 0,
            "attestations_given": 0,
        }

    @property
    def validator_did(self) -> Optional[str]:
        """The DID of this node's identity, if configured."""
        if self.identity is not None:
            return getattr(self.identity, "rings_did", None)
        return None

    # ==================================================================
    # Balance Queries
    # ==================================================================

    async def balance(self, did: str, token: str) -> int:
        """Get a DID's balance of a specific token.

        Checks local cache first, falls back to DHT lookup.

        Parameters
        ----------
        did : str
            The Rings DID to query.
        token : str
            Token identifier (e.g. ``"ETH"``, ``"0xa0b8..."``).

        Returns
        -------
        int
            The balance in the token's smallest unit.  Returns 0 if
            the DID has no balance for this token.
        """
        token = _normalize_token(token)

        # Check local cache
        if did in self._balances and token in self._balances[did]:
            return self._balances[did][token]

        # Fetch from DHT
        key = LedgerKeys.balance_key(did, token)
        raw = await self.client.dht_get(key)
        if raw is not None:
            amount = int(raw) if not isinstance(raw, int) else raw
            self._balances.setdefault(did, {})[token] = amount
            return amount

        return 0

    async def balances(self, did: str) -> Dict[str, int]:
        """Get all token balances for a DID.

        Returns the locally-cached view.  For a DID with no known
        balances, returns an empty dict.

        Parameters
        ----------
        did : str
            The Rings DID to query.

        Returns
        -------
        dict
            Map of ``token → balance``.
        """
        return dict(self._balances.get(did, {}))

    async def available_balance(self, did: str, token: str) -> int:
        """Get the available (unlocked) balance for a DID+token.

        This is ``balance - locked`` and represents the amount that
        can be transferred or withdrawn.

        Parameters
        ----------
        did : str
            The Rings DID.
        token : str
            The token identifier.

        Returns
        -------
        int
            Available balance (always ≥ 0).
        """
        token = _normalize_token(token)
        total = await self.balance(did, token)
        locked = self._get_locked(did, token)
        return max(0, total - locked)

    def _get_locked(self, did: str, token: str) -> int:
        """Get the total locked amount for a DID+token (from local cache)."""
        token = _normalize_token(token)
        return self._locks.get(did, {}).get(token, 0)

    async def _sync_lock_from_dht(self, did: str, token: str) -> int:
        """Fetch the locked amount from DHT and update local cache."""
        token = _normalize_token(token)
        key = LedgerKeys.lock_key(did, token)
        raw = await self.client.dht_get(key)
        locked = 0
        if raw is not None:
            locked = int(raw) if not isinstance(raw, int) else raw
        self._locks.setdefault(did, {})[token] = locked
        return locked

    # ==================================================================
    # Transfers (Agent-to-Agent on Rings)
    # ==================================================================

    async def transfer(
        self,
        from_did: str,
        to_did: str,
        token: str,
        amount: int,
        signature: bytes,
    ) -> TransferReceipt:
        """Initiate a transfer between two DIDs on Rings.

        Requires the sender's secp256k1 signature over the transfer
        intent (``sha256(from|to|token|amount|nonce)``).  The transfer
        goes through validator consensus (4/6 threshold) before
        finalizing.

        Parameters
        ----------
        from_did : str
            Sender's Rings DID.
        to_did : str
            Recipient's Rings DID.
        token : str
            Token identifier.
        amount : int
            Transfer amount in smallest unit.
        signature : bytes
            Sender's ECDSA signature over the transfer digest.

        Returns
        -------
        TransferReceipt
            Receipt with status (PROPOSED initially, or FAILED if
            validation fails).
        """
        token = _normalize_token(token)

        # --- Validation ---

        if amount <= 0:
            return TransferReceipt(
                transfer_id="",
                status=TransferStatus.FAILED,
                error="amount must be > 0",
            )

        if from_did == to_did:
            return TransferReceipt(
                transfer_id="",
                status=TransferStatus.FAILED,
                error="cannot transfer to self",
            )

        if not from_did or not to_did:
            return TransferReceipt(
                transfer_id="",
                status=TransferStatus.FAILED,
                error="from_did and to_did must be non-empty",
            )

        if not token:
            return TransferReceipt(
                transfer_id="",
                status=TransferStatus.FAILED,
                error="token must be non-empty",
            )

        # Check available balance
        available = await self.available_balance(from_did, token)
        if available < amount:
            return TransferReceipt(
                transfer_id="",
                status=TransferStatus.FAILED,
                error=(
                    f"insufficient balance: available={available}, "
                    f"requested={amount}"
                ),
            )

        # --- Create transfer ---
        async with self._lock:
            nonce = await self._get_next_nonce(from_did)

            transfer_id = str(uuid.uuid4())
            record = TransferRecord(
                transfer_id=transfer_id,
                from_did=from_did,
                to_did=to_did,
                token=token,
                amount=amount,
                nonce=nonce,
                signature=signature.hex() if isinstance(signature, bytes) else signature,
                status=TransferStatus.PROPOSED,
            )

            # Lock the sender's funds to prevent double-spend
            self._add_lock(from_did, token, amount)
            await self._persist_lock(from_did, token)

            # Store locally + DHT
            self._transfers[transfer_id] = record
            await self._persist_transfer(record)

            # Append to both sender's and recipient's history
            await self._append_history(from_did, transfer_id)
            await self._append_history(to_did, transfer_id)

            self._stats["transfers_proposed"] += 1

        logger.info(
            "Transfer proposed: id=%s, %s → %s, %d %s",
            transfer_id, from_did[:30], to_did[:30], amount, token,
        )

        # Broadcast to Sub-Ring
        await self._broadcast_ledger_message(
            LedgerMessage.TRANSFER_PROPOSED,
            {"transfer_id": transfer_id, "from_did": from_did,
             "to_did": to_did, "token": token, "amount": amount},
        )

        return TransferReceipt(
            transfer_id=transfer_id,
            status=TransferStatus.PROPOSED,
            attestation_count=0,
            threshold=self.threshold,
        )

    async def get_transfer(self, transfer_id: str) -> Optional[TransferRecord]:
        """Look up a transfer by ID.

        Checks local cache, then DHT.

        Parameters
        ----------
        transfer_id : str
            The transfer identifier.

        Returns
        -------
        TransferRecord or None
            The transfer record, or ``None`` if not found.
        """
        # Local cache
        if transfer_id in self._transfers:
            return self._transfers[transfer_id]

        # DHT lookup
        key = LedgerKeys.transfer_key(transfer_id)
        raw = await self.client.dht_get(key)
        if raw is not None and isinstance(raw, dict):
            record = TransferRecord.from_dict(raw)
            self._transfers[transfer_id] = record
            return record

        return None

    async def transfer_history(self, did: str, limit: int = 50) -> List[TransferRecord]:
        """Get transfer history for a DID (sent and received).

        Parameters
        ----------
        did : str
            The DID to query.
        limit : int
            Maximum number of records to return (newest first).

        Returns
        -------
        list of TransferRecord
        """
        key = LedgerKeys.history_key(did)
        raw = await self.client.dht_get(key)
        if raw is None:
            return []

        # raw should be a list of transfer_ids
        if not isinstance(raw, list):
            return []

        # Fetch the most recent `limit` transfer records
        ids = raw[-limit:] if len(raw) > limit else raw
        ids = list(reversed(ids))  # newest first

        records: List[TransferRecord] = []
        for tid in ids:
            rec = await self.get_transfer(tid)
            if rec is not None:
                records.append(rec)

        return records

    # ==================================================================
    # Bridge Integration
    # ==================================================================

    async def credit_from_bridge(
        self,
        did: str,
        token: str,
        amount: int,
        deposit_proof: Any = None,
    ) -> None:
        """Credit a DID after a verified bridge deposit.

        Called by the relayer after an Ethereum deposit has been
        verified and finalized (threshold attestations met).

        Parameters
        ----------
        did : str
            The Rings DID to credit.
        token : str
            Token identifier.
        amount : int
            Amount to credit in the token's smallest unit.
        deposit_proof : DepositRecord, optional
            The verified deposit record (for audit trail).

        Raises
        ------
        ValueError
            If amount ≤ 0 or DID is empty.
        """
        if amount <= 0:
            raise ValueError(f"credit amount must be > 0, got {amount}")
        if not did:
            raise ValueError("did must be non-empty")

        token = _normalize_token(token)

        async with self._lock:
            current = await self.balance(did, token)
            new_balance = current + amount
            self._balances.setdefault(did, {})[token] = new_balance

            # Persist to DHT
            await self._persist_balance(did, token, new_balance)
            self._stats["credits"] += 1

        logger.info(
            "Bridge credit: %s +%d %s (new balance: %d)",
            did[:30], amount, token, new_balance,
        )

        # Broadcast notification
        await self._broadcast_ledger_message(
            LedgerMessage.BALANCE_CREDITED,
            {"did": did, "token": token, "amount": amount,
             "new_balance": new_balance,
             "deposit_tx": (
                 deposit_proof.tx_hash if deposit_proof
                 and hasattr(deposit_proof, "tx_hash") else None
             )},
        )

    async def debit_for_withdrawal(
        self,
        did: str,
        token: str,
        amount: int,
    ) -> WithdrawalLock:
        """Lock tokens for a bridge withdrawal back to Ethereum.

        Creates a :class:`WithdrawalLock` that holds the tokens until
        the on-chain withdrawal completes (or is cancelled).

        Parameters
        ----------
        did : str
            The DID withdrawing tokens.
        token : str
            Token identifier.
        amount : int
            Amount to lock for withdrawal.

        Returns
        -------
        WithdrawalLock
            The lock record (pass to the bridge for on-chain execution).

        Raises
        ------
        ValueError
            If amount ≤ 0, DID is empty, or insufficient available balance.
        """
        if amount <= 0:
            raise ValueError(f"withdrawal amount must be > 0, got {amount}")
        if not did:
            raise ValueError("did must be non-empty")

        token = _normalize_token(token)

        async with self._lock:
            available = await self.available_balance(did, token)
            if available < amount:
                raise ValueError(
                    f"insufficient available balance: have {available}, "
                    f"need {amount} (token={token})"
                )

            # Create lock
            lock_id = str(uuid.uuid4())
            lock = WithdrawalLock(
                lock_id=lock_id,
                did=did,
                token=token,
                amount=amount,
            )

            # Lock the funds
            self._add_lock(did, token, amount)
            await self._persist_lock(did, token)

            # Store the lock record
            self._withdrawal_locks[lock_id] = lock
            wdlock_key = LedgerKeys.withdrawal_lock_key(lock_id)
            await self.client.dht_put(wdlock_key, lock.to_dict())

            self._stats["debits"] += 1

        logger.info(
            "Withdrawal lock: %s locked %d %s (lock_id=%s)",
            did[:30], amount, token, lock_id,
        )

        # Broadcast notification
        await self._broadcast_ledger_message(
            LedgerMessage.BALANCE_DEBITED,
            {"did": did, "token": token, "amount": amount,
             "lock_id": lock_id},
        )

        return lock

    async def release_withdrawal_lock(self, lock_id: str) -> None:
        """Release a withdrawal lock (e.g. after on-chain withdrawal completes).

        Deducts the locked amount from the DID's total balance and
        removes the lock.

        Parameters
        ----------
        lock_id : str
            The lock to release.

        Raises
        ------
        KeyError
            If the lock is not found.
        ValueError
            If the lock was already released.
        """
        lock = self._withdrawal_locks.get(lock_id)
        if lock is None:
            # Try DHT
            raw = await self.client.dht_get(
                LedgerKeys.withdrawal_lock_key(lock_id)
            )
            if raw is not None and isinstance(raw, dict):
                lock = WithdrawalLock.from_dict(raw)
                self._withdrawal_locks[lock_id] = lock
            else:
                raise KeyError(f"Unknown withdrawal lock: {lock_id}")

        if lock.released:
            raise ValueError(f"Lock {lock_id} already released")

        async with self._lock:
            did = lock.did
            token = _normalize_token(lock.token)
            amount = lock.amount

            # Remove the lock
            self._remove_lock(did, token, amount)
            await self._persist_lock(did, token)

            # Deduct from balance
            current = await self.balance(did, token)
            new_balance = max(0, current - amount)
            self._balances.setdefault(did, {})[token] = new_balance
            await self._persist_balance(did, token, new_balance)

            # Mark lock as released
            lock.released = True
            wdlock_key = LedgerKeys.withdrawal_lock_key(lock_id)
            await self.client.dht_put(wdlock_key, lock.to_dict())

        logger.info(
            "Withdrawal lock released: %s, %s -%d %s (new balance: %d)",
            lock_id, did[:30], amount, token, new_balance,
        )

    async def cancel_withdrawal_lock(self, lock_id: str) -> None:
        """Cancel a withdrawal lock (e.g. if on-chain withdrawal fails).

        Returns the locked tokens to the DID's available balance
        without deducting from total balance.

        Parameters
        ----------
        lock_id : str
            The lock to cancel.

        Raises
        ------
        KeyError
            If the lock is not found.
        ValueError
            If the lock was already released.
        """
        lock = self._withdrawal_locks.get(lock_id)
        if lock is None:
            raw = await self.client.dht_get(
                LedgerKeys.withdrawal_lock_key(lock_id)
            )
            if raw is not None and isinstance(raw, dict):
                lock = WithdrawalLock.from_dict(raw)
                self._withdrawal_locks[lock_id] = lock
            else:
                raise KeyError(f"Unknown withdrawal lock: {lock_id}")

        if lock.released:
            raise ValueError(f"Lock {lock_id} already released")

        async with self._lock:
            did = lock.did
            token = _normalize_token(lock.token)
            amount = lock.amount

            # Remove the lock (funds return to available)
            self._remove_lock(did, token, amount)
            await self._persist_lock(did, token)

            # Mark lock as released (cancelled)
            lock.released = True
            wdlock_key = LedgerKeys.withdrawal_lock_key(lock_id)
            await self.client.dht_put(wdlock_key, lock.to_dict())

        logger.info(
            "Withdrawal lock cancelled: %s, %s gets back %d %s",
            lock_id, did[:30], amount, token,
        )

    # ==================================================================
    # Validator Consensus for Transfers
    # ==================================================================

    async def propose_transfer(self, transfer: TransferRecord) -> str:
        """Propose a transfer to validators (store in DHT).

        This is called internally by :meth:`transfer` but can also be
        called directly for replaying a proposal.

        Parameters
        ----------
        transfer : TransferRecord
            The transfer to propose.

        Returns
        -------
        str
            The transfer_id.
        """
        transfer.status = TransferStatus.ATTESTING
        self._transfers[transfer.transfer_id] = transfer
        await self._persist_transfer(transfer)

        logger.info(
            "Transfer proposed for attestation: %s", transfer.transfer_id,
        )
        return transfer.transfer_id

    async def attest_transfer(self, transfer_id: str) -> Optional[bytes]:
        """Validator attests that a transfer is valid (sender has balance).

        The validator:
        1. Fetches the transfer record from DHT.
        2. Checks the sender's available balance ≥ transfer amount.
        3. Signs the attestation digest if valid.
        4. Records the attestation on the transfer record.

        Parameters
        ----------
        transfer_id : str
            The transfer to attest.

        Returns
        -------
        bytes or None
            The attestation signature, or ``None`` if rejected (insufficient
            balance, expired, or no identity configured).
        """
        if self.identity is None:
            logger.warning(
                "Cannot attest transfer %s: no identity configured",
                transfer_id,
            )
            return None

        record = await self.get_transfer(transfer_id)
        if record is None:
            logger.warning("Cannot attest: unknown transfer %s", transfer_id)
            return None

        # Check expiry
        if self._is_expired(record):
            logger.warning("Transfer %s has expired", transfer_id)
            record.status = TransferStatus.EXPIRED
            await self._persist_transfer(record)
            return None

        # Check status — only attest PROPOSED or ATTESTING transfers
        if record.status not in (TransferStatus.PROPOSED, TransferStatus.ATTESTING):
            logger.warning(
                "Cannot attest transfer %s in state %s",
                transfer_id, record.status.value,
            )
            return None

        # Check that we haven't already attested
        validator_did = self.validator_did
        if validator_did and validator_did in record.attestations:
            logger.debug(
                "Already attested transfer %s", transfer_id,
            )
            return bytes.fromhex(record.attestations[validator_did])

        # Verify sender has sufficient balance
        available = await self.available_balance(record.from_did, record.token)
        # The sender's funds for THIS transfer are already locked,
        # so we check that the lock exists (balance ≥ locked ≥ amount)
        total_bal = await self.balance(record.from_did, record.token)
        if total_bal < record.amount:
            reason = (
                f"sender balance {total_bal} < transfer amount {record.amount}"
            )
            logger.warning(
                "Rejecting transfer %s: %s", transfer_id, reason,
            )
            if validator_did:
                record.rejection_reasons[validator_did] = reason
                await self._persist_transfer(record)
            return None

        # Sign attestation
        digest = _compute_attestation_digest(
            transfer_id, record.from_did, record.amount,
        )
        signature = self.identity.sign_rings(digest)

        # Record attestation
        async with self._lock:
            if validator_did:
                record.attestations[validator_did] = signature.hex()
            record.status = TransferStatus.ATTESTING
            await self._persist_transfer(record)
            self._stats["attestations_given"] += 1

        logger.info(
            "Attested transfer %s (attestation %d/%d)",
            transfer_id, len(record.attestations), self.threshold,
        )

        # Broadcast attestation
        await self._broadcast_ledger_message(
            LedgerMessage.TRANSFER_ATTESTED,
            {"transfer_id": transfer_id,
             "validator": validator_did,
             "attestation_count": len(record.attestations)},
        )

        return signature

    async def collect_transfer_attestations(
        self, transfer_id: str
    ) -> Tuple[bool, List[bytes]]:
        """Collect attestations for a transfer.  Finalize if threshold met.

        Reads the latest attestations from the DHT, merges with local
        state, and checks the threshold.  If ≥ *threshold* attestations
        have been collected, the transfer is atomically finalized:
        sender's balance decremented, recipient's balance incremented,
        and the transfer lock released.

        Parameters
        ----------
        transfer_id : str
            The transfer to check.

        Returns
        -------
        tuple of (bool, list of bytes)
            ``(threshold_met, list_of_attestation_signatures)``.
        """
        # Fetch from DHT to merge any remote attestations
        key = LedgerKeys.transfer_key(transfer_id)
        raw = await self.client.dht_get(key)

        local_record = self._transfers.get(transfer_id)

        if raw is None and local_record is None:
            return False, []

        if raw is not None and isinstance(raw, dict):
            dht_record = TransferRecord.from_dict(raw)
            # Merge attestations
            if local_record is not None:
                for vid, sig in dht_record.attestations.items():
                    if vid not in local_record.attestations:
                        local_record.attestations[vid] = sig
                record = local_record
            else:
                record = dht_record
                self._transfers[transfer_id] = record
        else:
            record = local_record  # type: ignore[assignment]

        # Check if already finalized
        if record.status == TransferStatus.FINALIZED:
            sigs = [bytes.fromhex(s) for s in record.attestations.values()]
            return True, sigs

        # Check expiry
        if self._is_expired(record):
            record.status = TransferStatus.EXPIRED
            await self._persist_transfer(record)
            return False, []

        signatures = list(record.attestations.values())
        sig_bytes = [bytes.fromhex(s) for s in signatures]
        threshold_met = len(signatures) >= self.threshold

        if threshold_met and record.status != TransferStatus.FINALIZED:
            # Finalize: update balances atomically
            await self._finalize_transfer(record)

        return threshold_met, sig_bytes

    async def _finalize_transfer(self, record: TransferRecord) -> None:
        """Atomically finalize a transfer: move funds and release lock.

        Parameters
        ----------
        record : TransferRecord
            The transfer to finalize (must have ≥ threshold attestations).
        """
        async with self._lock:
            from_did = record.from_did
            to_did = record.to_did
            token = _normalize_token(record.token)
            amount = record.amount

            # Deduct from sender
            sender_balance = await self.balance(from_did, token)
            new_sender_balance = max(0, sender_balance - amount)
            self._balances.setdefault(from_did, {})[token] = new_sender_balance
            await self._persist_balance(from_did, token, new_sender_balance)

            # Credit recipient
            recipient_balance = await self.balance(to_did, token)
            new_recipient_balance = recipient_balance + amount
            self._balances.setdefault(to_did, {})[token] = new_recipient_balance
            await self._persist_balance(to_did, token, new_recipient_balance)

            # Release the transfer lock
            self._remove_lock(from_did, token, amount)
            await self._persist_lock(from_did, token)

            # Update transfer status
            record.status = TransferStatus.FINALIZED
            record.finalized_at = time.time()
            await self._persist_transfer(record)

            self._stats["transfers_finalized"] += 1

        logger.info(
            "Transfer finalized: %s, %s → %s, %d %s "
            "(sender_bal=%d, recipient_bal=%d)",
            record.transfer_id,
            from_did[:30], to_did[:30],
            amount, token,
            new_sender_balance, new_recipient_balance,
        )

        # Broadcast finalization
        await self._broadcast_ledger_message(
            LedgerMessage.TRANSFER_FINALIZED,
            {"transfer_id": record.transfer_id,
             "from_did": from_did, "to_did": to_did,
             "token": token, "amount": amount},
        )

    async def fail_transfer(
        self, transfer_id: str, reason: str = ""
    ) -> None:
        """Mark a transfer as failed and release the lock.

        Parameters
        ----------
        transfer_id : str
            The transfer to fail.
        reason : str
            Human-readable failure reason.
        """
        record = await self.get_transfer(transfer_id)
        if record is None:
            raise KeyError(f"Unknown transfer: {transfer_id}")

        if record.status in (TransferStatus.FINALIZED, TransferStatus.FAILED):
            return  # Already terminal

        async with self._lock:
            # Release the lock
            token = _normalize_token(record.token)
            self._remove_lock(record.from_did, token, record.amount)
            await self._persist_lock(record.from_did, token)

            # Update status
            record.status = TransferStatus.FAILED
            record.error = reason
            await self._persist_transfer(record)

            self._stats["transfers_failed"] += 1

        logger.warning(
            "Transfer failed: %s — %s", transfer_id, reason,
        )

        await self._broadcast_ledger_message(
            LedgerMessage.TRANSFER_FAILED,
            {"transfer_id": transfer_id, "reason": reason},
        )

    # ==================================================================
    # Nonce Management
    # ==================================================================

    async def get_nonce(self, did: str) -> int:
        """Get the current nonce for a DID (next expected nonce).

        Parameters
        ----------
        did : str
            The DID to query.

        Returns
        -------
        int
            The next expected nonce (0 if no transfers yet).
        """
        if did in self._nonces:
            return self._nonces[did]

        key = LedgerKeys.nonce_key(did)
        raw = await self.client.dht_get(key)
        if raw is not None:
            nonce = int(raw) if not isinstance(raw, int) else raw
            self._nonces[did] = nonce
            return nonce

        return 0

    async def _get_next_nonce(self, did: str) -> int:
        """Get and increment the nonce for a DID.

        Returns the nonce to use for the current transfer, then
        increments the stored nonce.

        Parameters
        ----------
        did : str
            The sender's DID.

        Returns
        -------
        int
            The nonce value for this transfer.
        """
        current = await self.get_nonce(did)
        next_nonce = current + 1
        self._nonces[did] = next_nonce

        # Persist to DHT
        key = LedgerKeys.nonce_key(did)
        await self.client.dht_put(key, next_nonce)

        return current

    # ==================================================================
    # Expiry Management
    # ==================================================================

    def _is_expired(self, record: TransferRecord) -> bool:
        """Check whether a transfer has exceeded its TTL."""
        return (time.time() - record.timestamp) > self.transfer_ttl

    async def expire_stale_transfers(self) -> int:
        """Scan all local transfers and expire stale ones.

        Releases locks for expired transfers and updates their status.

        Returns
        -------
        int
            Number of transfers expired.
        """
        expired_count = 0

        async with self._lock:
            for tid, record in list(self._transfers.items()):
                if (
                    record.status in (TransferStatus.PROPOSED, TransferStatus.ATTESTING)
                    and self._is_expired(record)
                ):
                    # Release lock
                    token = _normalize_token(record.token)
                    self._remove_lock(record.from_did, token, record.amount)
                    await self._persist_lock(record.from_did, token)

                    record.status = TransferStatus.EXPIRED
                    record.error = "attestation window expired"
                    await self._persist_transfer(record)
                    expired_count += 1

        if expired_count > 0:
            logger.info("Expired %d stale transfers", expired_count)

        return expired_count

    # ==================================================================
    # Statistics
    # ==================================================================

    @property
    def stats(self) -> Dict[str, Any]:
        """Current ledger statistics (non-async, snapshot)."""
        return {
            **self._stats,
            "known_dids": len(self._balances),
            "active_transfers": sum(
                1 for r in self._transfers.values()
                if r.status in (TransferStatus.PROPOSED, TransferStatus.ATTESTING)
            ),
            "total_transfers": len(self._transfers),
            "active_withdrawal_locks": sum(
                1 for l in self._withdrawal_locks.values()
                if not l.released
            ),
            "threshold": self.threshold,
            "total_validators": self.total,
        }

    # ==================================================================
    # Internal: Lock Management
    # ==================================================================

    def _add_lock(self, did: str, token: str, amount: int) -> None:
        """Add to the locked amount for a DID+token (local cache)."""
        token = _normalize_token(token)
        current = self._locks.get(did, {}).get(token, 0)
        self._locks.setdefault(did, {})[token] = current + amount

    def _remove_lock(self, did: str, token: str, amount: int) -> None:
        """Remove from the locked amount for a DID+token (local cache)."""
        token = _normalize_token(token)
        current = self._locks.get(did, {}).get(token, 0)
        new_val = max(0, current - amount)
        self._locks.setdefault(did, {})[token] = new_val

    # ==================================================================
    # Internal: DHT Persistence
    # ==================================================================

    async def _persist_balance(self, did: str, token: str, amount: int) -> None:
        """Write a balance to the DHT."""
        key = LedgerKeys.balance_key(did, token)
        await self.client.dht_put(key, amount)

    async def _persist_lock(self, did: str, token: str) -> None:
        """Write the locked amount to the DHT."""
        token = _normalize_token(token)
        locked = self._locks.get(did, {}).get(token, 0)
        key = LedgerKeys.lock_key(did, token)
        await self.client.dht_put(key, locked)

    async def _persist_transfer(self, record: TransferRecord) -> None:
        """Write a transfer record to the DHT."""
        key = LedgerKeys.transfer_key(record.transfer_id)
        await self.client.dht_put(key, record.to_dict())

    async def _append_history(self, did: str, transfer_id: str) -> None:
        """Append a transfer_id to a DID's history list in the DHT.

        Uses the DHT ``Extend`` operator for append semantics.
        Trims to ``MAX_HISTORY_PER_DID`` entries.
        """
        key = LedgerKeys.history_key(did)

        # Fetch current history
        raw = await self.client.dht_get(key)
        if raw is None:
            history: List[str] = []
        elif isinstance(raw, list):
            history = raw
        else:
            history = [raw]

        history.append(transfer_id)

        # Trim if too large
        if len(history) > MAX_HISTORY_PER_DID:
            history = history[-MAX_HISTORY_PER_DID:]

        await self.client.dht_put(key, history)

    # ==================================================================
    # Internal: Sub-Ring Messaging
    # ==================================================================

    async def _broadcast_ledger_message(
        self, msg_type: LedgerMessage, payload: Dict[str, Any]
    ) -> None:
        """Broadcast a ledger message to the bridge Sub-Ring.

        Parameters
        ----------
        msg_type : LedgerMessage
            The message type.
        payload : dict
            Message-specific data.
        """
        try:
            msg = {
                "type": msg_type.value,
                "payload": payload,
                "timestamp": time.time(),
            }
            await self.client.broadcast(self.BRIDGE_SUBRING, msg)
        except Exception as exc:
            # Don't fail the operation if broadcast fails
            logger.debug("Broadcast failed (non-critical): %s", exc)

    # ==================================================================
    # Bulk Operations
    # ==================================================================

    async def credit_multiple(
        self,
        credits: List[Tuple[str, str, int]],
    ) -> int:
        """Credit multiple DID+token pairs in one batch.

        Parameters
        ----------
        credits : list of (did, token, amount)
            Each tuple is (DID, token_id, amount_to_credit).

        Returns
        -------
        int
            Number of credits applied.
        """
        count = 0
        for did, token, amount in credits:
            try:
                await self.credit_from_bridge(did, token, amount)
                count += 1
            except Exception as exc:
                logger.error(
                    "Failed to credit %s %d %s: %s",
                    did[:30], amount, token, exc,
                )
        return count

    # ==================================================================
    # Signature Verification
    # ==================================================================

    def verify_transfer_signature(
        self,
        record: TransferRecord,
        public_key_obj: Any = None,
    ) -> bool:
        """Verify the sender's signature on a transfer record.

        The signature covers ``sha256(from_did|to_did|token|amount|nonce)``.

        Parameters
        ----------
        record : TransferRecord
            The transfer to verify.
        public_key_obj : cryptography key object, optional
            The sender's public key.  If ``None``, verification is
            skipped (returns ``True`` for permissionless mode).

        Returns
        -------
        bool
            ``True`` if the signature is valid.
        """
        if public_key_obj is None:
            # In permissionless mode without key resolution, skip
            return True

        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.exceptions import InvalidSignature

            digest = _compute_transfer_digest(
                record.from_did, record.to_did,
                record.token, record.amount, record.nonce,
            )
            sig_bytes = bytes.fromhex(record.signature)

            # Verify ECDSA-SHA256 (same as Rings protocol signing)
            public_key_obj.verify(sig_bytes, digest, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False
        except Exception as exc:
            logger.debug("Signature verification error: %s", exc)
            return False

    def verify_attestation_signature(
        self,
        transfer_id: str,
        from_did: str,
        amount: int,
        signature_hex: str,
        public_key_obj: Any = None,
    ) -> bool:
        """Verify a validator's attestation signature.

        The signature covers ``sha256(transfer_id|from_did|amount)``.

        Parameters
        ----------
        transfer_id : str
            The transfer being attested.
        from_did : str
            The sender's DID.
        amount : int
            Transfer amount.
        signature_hex : str
            Hex-encoded attestation signature.
        public_key_obj : cryptography key object, optional
            The validator's public key.

        Returns
        -------
        bool
            ``True`` if the signature is valid.
        """
        if public_key_obj is None:
            return True

        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.exceptions import InvalidSignature

            digest = _compute_attestation_digest(transfer_id, from_did, amount)
            sig_bytes = bytes.fromhex(signature_hex)

            public_key_obj.verify(sig_bytes, digest, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False
        except Exception as exc:
            logger.debug("Attestation signature verification error: %s", exc)
            return False

    # ==================================================================
    # Dunder
    # ==================================================================

    def __repr__(self) -> str:
        return (
            f"RingsTokenLedger("
            f"dids={len(self._balances)}, "
            f"transfers={len(self._transfers)}, "
            f"threshold={self.threshold}/{self.total})"
        )
