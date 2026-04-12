"""
Ethereum Light Client Verification
====================================

Abstract interface for Ethereum light client verification, along with a
Helios stub (for future Rust FFI integration) and a fully-functional
in-memory mock for testing.

Ethereum's Proof-of-Stake consensus relies on sync committees — rotating
groups of 512 validators that sign every slot's block header. A light
client tracks these committee rotations and can verify any header
with just:

1. The current sync committee's aggregate BLS public key.
2. The sync committee's aggregate signature over the slot.
3. A chain of Merkle proofs from the header's ``state_root`` to the
   data of interest.

This module provides:

- :class:`EthLightClient` — the abstract interface.
- :class:`HeliosLightClient` — stub for the Helios Rust light client
  (to be implemented via PyO3 FFI).
- :class:`MockLightClient` — in-memory mock that stores headers, proofs,
  and committees for deterministic testing.
- Data classes: :class:`BeaconHeader`, :class:`SyncCommittee`,
  :class:`StateProof`, :class:`EventProof`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BeaconHeader:
    """Ethereum Beacon Chain block header.

    A minimal representation of the
    `BeaconBlockHeader <https://eth2book.info/capella/part3/containers/dependencies/#beaconblockheader>`_
    used by the consensus layer.

    Attributes
    ----------
    slot : int
        Slot number (one slot = 12 seconds on mainnet).
    proposer_index : int
        Index of the validator that proposed this block.
    parent_root : str
        Hex-encoded root hash of the parent block.
    state_root : str
        Hex-encoded root hash of the post-state.
    body_root : str
        Hex-encoded root hash of the block body.
    timestamp : int
        Unix timestamp (seconds) of the slot.
    """

    slot: int
    proposer_index: int
    parent_root: str  # hex
    state_root: str  # hex
    body_root: str  # hex
    timestamp: int = 0

    def header_root(self) -> str:
        """Compute a deterministic hash of this header (mock SSZ root).

        .. note::

            In production, this would be a proper SSZ hash-tree-root.
            For testing, we use SHA-256 over the concatenated fields.
        """
        data = (
            f"{self.slot}|{self.proposer_index}|"
            f"{self.parent_root}|{self.state_root}|{self.body_root}"
        ).encode()
        return hashlib.sha256(data).hexdigest()


@dataclass
class SyncCommittee:
    """Ethereum sync committee snapshot.

    Each sync committee period spans 256 epochs (≈ 27 hours on mainnet).
    The committee consists of 512 validators whose BLS public keys
    are aggregated for efficient signature verification.

    Attributes
    ----------
    period : int
        The sync committee period number.
    pubkeys : list of str
        BLS12-381 public key hex strings for committee members.
    aggregate_pubkey : str
        The aggregate BLS12-381 public key (hex).
    """

    period: int
    pubkeys: List[str]  # BLS12-381 public keys
    aggregate_pubkey: str


@dataclass
class StateProof:
    """Ethereum state proof (EIP-1186 ``eth_getProof`` response).

    Proves the state of an account at a specific block, including
    nonce, balance, code hash, storage hash, and optionally
    specific storage slots.

    Attributes
    ----------
    address : str
        The ``0x``-prefixed Ethereum address.
    balance : int
        Account balance in wei.
    nonce : int
        Account nonce (transaction count).
    code_hash : str
        Hex-encoded keccak256 of the account's bytecode (or
        ``keccak256("")`` for EOAs).
    storage_hash : str
        Hex-encoded root hash of the account's storage trie.
    account_proof : list of str
        Hex-encoded RLP-encoded Merkle-Patricia Trie nodes from the
        state root to the account leaf.
    storage_proofs : dict
        Mapping of storage key → ``{"value": str, "proof": [str]}``.
    block_number : int
        Block at which the proof was generated.
    verified : bool
        Whether the proof has been cryptographically verified.
    """

    address: str
    balance: int
    nonce: int
    code_hash: str
    storage_hash: str
    account_proof: List[str]  # hex-encoded RLP nodes
    storage_proofs: Dict[str, Any]  # key → value + proof
    block_number: int
    verified: bool = False


@dataclass
class EventProof:
    """Ethereum event (log) proof.

    Proves that a specific log entry exists in a transaction receipt,
    verified against the block's receipts root.

    Attributes
    ----------
    tx_hash : str
        Transaction hash containing the event.
    log_index : int
        Index of the log within the receipt.
    address : str
        Contract address that emitted the event.
    topics : list of str
        Hex-encoded event topics (topic[0] = event signature hash).
    data : str
        Hex-encoded non-indexed event data.
    block_number : int
        Block number of the transaction.
    receipt_proof : list of str
        Hex-encoded RLP nodes proving the receipt in the receipts trie.
    verified : bool
        Whether the proof has been cryptographically verified.
    """

    tx_hash: str
    log_index: int
    address: str
    topics: List[str]
    data: str  # hex
    block_number: int
    receipt_proof: List[str]
    verified: bool = False


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class EthLightClient(ABC):
    """Abstract Ethereum light client interface.

    Implementations must provide sync, header verification, state proof
    verification, event proof verification, and sync committee tracking.
    """

    @abstractmethod
    async def sync(self, checkpoint: str) -> None:
        """Initialize the light client from a trusted checkpoint.

        Parameters
        ----------
        checkpoint : str
            A trusted block root (hex) to start syncing from.
        """

    @abstractmethod
    async def get_verified_header(self, slot: int) -> BeaconHeader:
        """Get a verified Beacon header for a given slot.

        Parameters
        ----------
        slot : int
            The slot number.

        Returns
        -------
        BeaconHeader

        Raises
        ------
        KeyError
            If the header is not available.
        """

    @abstractmethod
    async def verify_state_proof(
        self,
        address: str,
        storage_keys: List[str],
        block: int,
    ) -> StateProof:
        """Verify an Ethereum state proof (EIP-1186).

        Parameters
        ----------
        address : str
            Ethereum address to prove.
        storage_keys : list of str
            Storage slot keys to include.
        block : int
            Block number for the proof.

        Returns
        -------
        StateProof
        """

    @abstractmethod
    async def verify_event(self, tx_hash: str, log_index: int) -> EventProof:
        """Verify that a specific event exists in a transaction receipt.

        Parameters
        ----------
        tx_hash : str
            Transaction hash.
        log_index : int
            Log index within the receipt.

        Returns
        -------
        EventProof
        """

    @abstractmethod
    async def get_sync_committee(self, period: int) -> SyncCommittee:
        """Get the sync committee for a given period.

        Parameters
        ----------
        period : int
            Sync committee period number.

        Returns
        -------
        SyncCommittee
        """

    @abstractmethod
    async def get_latest_slot(self) -> int:
        """Get the latest verified slot number.

        Returns
        -------
        int
        """

    @property
    @abstractmethod
    def is_synced(self) -> bool:
        """Whether the light client has completed initial sync."""


# ---------------------------------------------------------------------------
# Helios stub (future Rust FFI)
# ---------------------------------------------------------------------------

_HELIOS_NOT_IMPL_MSG = (
    "Helios FFI not yet implemented — use MockLightClient for testing. "
    "See https://github.com/a16z/helios for the Rust implementation."
)


class HeliosLightClient(EthLightClient):
    """Stub for the `Helios <https://github.com/a16z/helios>`_ Rust
    light client.

    All methods raise :class:`NotImplementedError` with a helpful
    message. Future implementation will use PyO3 FFI to call into the
    Helios Rust binary.

    Parameters
    ----------
    helios_binary : str
        Path to the Helios binary.
    checkpoint : str
        Initial trusted checkpoint block root (hex).
    network : str
        Ethereum network name (``"mainnet"``, ``"goerli"``, etc.).
    """

    def __init__(
        self,
        helios_binary: str = "helios",
        checkpoint: str = "",
        network: str = "mainnet",
    ) -> None:
        self._binary = helios_binary
        self._checkpoint = checkpoint
        self._network = network
        self._synced = False

    async def sync(self, checkpoint: str) -> None:
        raise NotImplementedError(_HELIOS_NOT_IMPL_MSG)

    async def get_verified_header(self, slot: int) -> BeaconHeader:
        raise NotImplementedError(_HELIOS_NOT_IMPL_MSG)

    async def verify_state_proof(
        self, address: str, storage_keys: List[str], block: int
    ) -> StateProof:
        raise NotImplementedError(_HELIOS_NOT_IMPL_MSG)

    async def verify_event(self, tx_hash: str, log_index: int) -> EventProof:
        raise NotImplementedError(_HELIOS_NOT_IMPL_MSG)

    async def get_sync_committee(self, period: int) -> SyncCommittee:
        raise NotImplementedError(_HELIOS_NOT_IMPL_MSG)

    async def get_latest_slot(self) -> int:
        raise NotImplementedError(_HELIOS_NOT_IMPL_MSG)

    @property
    def is_synced(self) -> bool:
        return self._synced

    def __repr__(self) -> str:
        return (
            f"HeliosLightClient(binary={self._binary!r}, "
            f"network={self._network!r}, synced={self._synced})"
        )


# ---------------------------------------------------------------------------
# Mock light client (for testing)
# ---------------------------------------------------------------------------


class MockLightClient(EthLightClient):
    """In-memory mock Ethereum light client for testing.

    Pre-populate with headers, committees, and proofs using the
    ``add_*`` helper methods, then use the standard
    :class:`EthLightClient` interface to query them.

    Example
    -------
    ::

        lc = MockLightClient()
        header = BeaconHeader(slot=100, proposer_index=42,
                              parent_root="0xaa", state_root="0xbb",
                              body_root="0xcc")
        lc.add_header(header)
        await lc.sync("0xaa")

        h = await lc.get_verified_header(100)
        assert h.slot == 100
    """

    def __init__(self) -> None:
        self._headers: Dict[int, BeaconHeader] = {}
        self._committees: Dict[int, SyncCommittee] = {}
        self._state_proofs: Dict[str, StateProof] = {}  # "addr:block" → proof
        self._event_proofs: Dict[str, EventProof] = {}  # "tx:logidx" → proof
        self._synced = False
        self._latest_slot = 0
        self._checkpoint: str = ""

    # ── Test setup helpers ───────────────────────────────────────────────

    def add_header(self, header: BeaconHeader) -> None:
        """Pre-populate a Beacon header.

        Also updates ``_latest_slot`` if this header has a higher slot.

        Parameters
        ----------
        header : BeaconHeader
            The header to store.
        """
        self._headers[header.slot] = header
        if header.slot > self._latest_slot:
            self._latest_slot = header.slot

    def add_state_proof(self, proof: StateProof) -> None:
        """Pre-populate a state proof.

        Parameters
        ----------
        proof : StateProof
            Keyed by ``"{address}:{block_number}"``.
        """
        key = f"{proof.address}:{proof.block_number}"
        self._state_proofs[key] = proof

    def add_event_proof(self, proof: EventProof) -> None:
        """Pre-populate an event proof.

        Parameters
        ----------
        proof : EventProof
            Keyed by ``"{tx_hash}:{log_index}"``.
        """
        key = f"{proof.tx_hash}:{proof.log_index}"
        self._event_proofs[key] = proof

    def add_sync_committee(self, committee: SyncCommittee) -> None:
        """Pre-populate a sync committee.

        Parameters
        ----------
        committee : SyncCommittee
        """
        self._committees[committee.period] = committee

    # ── EthLightClient interface ─────────────────────────────────────────

    async def sync(self, checkpoint: str) -> None:
        """Mark the mock client as synced from the given checkpoint.

        Parameters
        ----------
        checkpoint : str
            Trusted block root (hex). Stored for reference.
        """
        self._checkpoint = checkpoint
        self._synced = True
        logger.info("MockLightClient synced from checkpoint %s", checkpoint)

    async def get_verified_header(self, slot: int) -> BeaconHeader:
        """Return a pre-populated header.

        Raises
        ------
        KeyError
            If no header exists for the given slot.
        """
        if slot not in self._headers:
            raise KeyError(f"No header for slot {slot}")
        return self._headers[slot]

    async def verify_state_proof(
        self,
        address: str,
        storage_keys: List[str],
        block: int,
    ) -> StateProof:
        """Return a pre-populated state proof, marked as verified.

        Raises
        ------
        KeyError
            If no state proof exists for the given address/block.
        """
        key = f"{address}:{block}"
        if key not in self._state_proofs:
            raise KeyError(f"No state proof for {key}")
        proof = self._state_proofs[key]
        proof.verified = True
        return proof

    async def verify_event(self, tx_hash: str, log_index: int) -> EventProof:
        """Return a pre-populated event proof, marked as verified.

        Raises
        ------
        KeyError
            If no event proof exists for the given tx_hash/log_index.
        """
        key = f"{tx_hash}:{log_index}"
        if key not in self._event_proofs:
            raise KeyError(f"No event proof for {key}")
        proof = self._event_proofs[key]
        proof.verified = True
        return proof

    async def get_sync_committee(self, period: int) -> SyncCommittee:
        """Return a pre-populated sync committee.

        Raises
        ------
        KeyError
            If no committee exists for the given period.
        """
        if period not in self._committees:
            raise KeyError(f"No sync committee for period {period}")
        return self._committees[period]

    async def get_latest_slot(self) -> int:
        """Return the highest slot among stored headers."""
        return self._latest_slot

    @property
    def is_synced(self) -> bool:
        """Whether :meth:`sync` has been called."""
        return self._synced

    def __repr__(self) -> str:
        return (
            f"MockLightClient(synced={self._synced}, "
            f"headers={len(self._headers)}, "
            f"committees={len(self._committees)}, "
            f"state_proofs={len(self._state_proofs)}, "
            f"event_proofs={len(self._event_proofs)})"
        )
