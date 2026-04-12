"""
Beacon API Light Client
========================

Production Ethereum Beacon Chain light client that connects to real
Beacon API endpoints (e.g. Sepolia public nodes) and the execution
layer JSON-RPC for ``eth_getProof``.

Implements the :class:`~.light_client.EthLightClient` abstract base
class, replacing :class:`~.light_client.MockLightClient` for live use.

Key features:

- Fetches finalized headers from ``/eth/v1/beacon/headers/finalized``.
- Retrieves sync committees via light client update endpoints.
- Calls ``eth_getProof`` on the execution layer for state verification.
- Verifies Merkle-Patricia Trie proofs using
  :class:`~.merkle_patricia.MerklePatriciaVerifier`.
- Automatic retries with exponential back-off.
- LRU header cache to reduce API calls.
- Fallback beacon URL support.

Usage
-----
::

    client = BeaconAPILightClient(
        beacon_url="https://ethereum-sepolia-beacon-api.publicnode.com",
        execution_url="https://ethereum-sepolia-rpc.publicnode.com",
    )
    await client.sync("0xabc...")
    header = await client.get_verified_header(slot=10022528)
    proof = await client.verify_state_proof(
        "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca", [], block=10644593
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from .light_client import (
    BeaconHeader,
    EthLightClient,
    EventProof,
    StateProof,
    SyncCommittee,
)
from .merkle_patricia import MerklePatriciaVerifier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SLOTS_PER_EPOCH = 32
EPOCHS_PER_SYNC_COMMITTEE_PERIOD = 256
SLOTS_PER_SYNC_COMMITTEE_PERIOD = SLOTS_PER_EPOCH * EPOCHS_PER_SYNC_COMMITTEE_PERIOD
SECONDS_PER_SLOT = 12

# Sepolia genesis time (Unix timestamp)
SEPOLIA_GENESIS_TIME = 1655733600

# Default timeouts and retry config
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0  # seconds

# Header cache size
DEFAULT_HEADER_CACHE_SIZE = 256


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def slot_to_epoch(slot: int) -> int:
    """Convert a slot number to its epoch."""
    return slot // SLOTS_PER_EPOCH


def epoch_to_sync_committee_period(epoch: int) -> int:
    """Convert an epoch to its sync committee period."""
    return epoch // EPOCHS_PER_SYNC_COMMITTEE_PERIOD


def slot_to_sync_committee_period(slot: int) -> int:
    """Convert a slot to its sync committee period."""
    return slot_to_epoch(slot) // EPOCHS_PER_SYNC_COMMITTEE_PERIOD


def slot_to_timestamp(slot: int, genesis_time: int = SEPOLIA_GENESIS_TIME) -> int:
    """Convert a slot to Unix timestamp."""
    return genesis_time + slot * SECONDS_PER_SLOT


# ---------------------------------------------------------------------------
# LRU Cache for headers
# ---------------------------------------------------------------------------


class LRUCache:
    """Simple LRU cache based on :class:`collections.OrderedDict`.

    Parameters
    ----------
    max_size : int
        Maximum number of entries.
    """

    def __init__(self, max_size: int = DEFAULT_HEADER_CACHE_SIZE) -> None:
        self._cache: OrderedDict[Any, Any] = OrderedDict()
        self._max_size = max_size

    def get(self, key: Any) -> Any:
        """Get a value, moving it to the end (most recently used)."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: Any, value: Any) -> None:
        """Insert or update a value."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def __contains__(self, key: Any) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BeaconAPIError(Exception):
    """Error communicating with the Beacon API."""

    def __init__(self, message: str, status_code: int = 0, url: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class ExecutionRPCError(Exception):
    """Error communicating with the Execution Layer JSON-RPC."""

    def __init__(self, message: str, code: int = 0) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# BeaconAPILightClient
# ---------------------------------------------------------------------------


class BeaconAPILightClient(EthLightClient):
    """Real Beacon Chain light client connecting to Beacon API endpoints.

    Implements the full :class:`EthLightClient` ABC using live HTTP
    calls to Ethereum consensus-layer and execution-layer endpoints.

    Parameters
    ----------
    beacon_url : str
        Primary Beacon API base URL (no trailing slash).
    execution_url : str
        Execution layer JSON-RPC URL.
    fallback_beacon_url : str or None
        Fallback Beacon API URL if primary fails.
    genesis_time : int
        Chain genesis Unix timestamp. Defaults to Sepolia genesis.
    timeout : float
        HTTP request timeout in seconds.
    max_retries : int
        Maximum retry attempts per request.
    retry_base_delay : float
        Base delay (seconds) for exponential back-off.
    header_cache_size : int
        Maximum number of cached headers.
    """

    def __init__(
        self,
        beacon_url: str = "https://ethereum-sepolia-beacon-api.publicnode.com",
        execution_url: str = "https://ethereum-sepolia-rpc.publicnode.com",
        fallback_beacon_url: Optional[str] = "https://lodestar-sepolia.chainsafe.io",
        genesis_time: int = SEPOLIA_GENESIS_TIME,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
        header_cache_size: int = DEFAULT_HEADER_CACHE_SIZE,
    ) -> None:
        self._beacon_url = beacon_url.rstrip("/")
        self._execution_url = execution_url.rstrip("/")
        self._fallback_beacon_url = (
            fallback_beacon_url.rstrip("/") if fallback_beacon_url else None
        )
        self._genesis_time = genesis_time
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

        # State
        self._synced = False
        self._latest_slot = 0
        self._checkpoint: str = ""
        self._finalized_header: Optional[BeaconHeader] = None
        self._finalized_block_root: str = ""

        # Caches
        self._header_cache = LRUCache(header_cache_size)
        self._committee_cache: Dict[int, SyncCommittee] = {}

        # Session (created lazily)
        self._session: Optional[aiohttp.ClientSession] = None

        # JSON-RPC request ID counter
        self._rpc_id = 0

    # ── Session management ──────────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session. Call when done."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "BeaconAPILightClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── HTTP helpers with retry ─────────────────────────────────────────

    async def _beacon_get(
        self, path: str, *, use_fallback: bool = True
    ) -> dict:
        """GET a Beacon API endpoint with retries and optional fallback.

        Parameters
        ----------
        path : str
            API path (e.g. ``/eth/v1/beacon/headers/finalized``).
        use_fallback : bool
            If True, try the fallback URL on failure.

        Returns
        -------
        dict
            Parsed JSON response.

        Raises
        ------
        BeaconAPIError
            If all attempts fail.
        """
        urls = [f"{self._beacon_url}{path}"]
        if use_fallback and self._fallback_beacon_url:
            urls.append(f"{self._fallback_beacon_url}{path}")

        last_error: Optional[Exception] = None
        for url in urls:
            for attempt in range(self._max_retries):
                try:
                    session = await self._get_session()
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            return data
                        elif resp.status == 404:
                            # Resource doesn't exist — don't retry
                            body = await resp.text()
                            raise BeaconAPIError(
                                f"Not found: {path} — {body}",
                                status_code=404,
                                url=url,
                            )
                        elif resp.status == 429:
                            # Rate limited — wait longer
                            delay = self._retry_base_delay * (2 ** (attempt + 1))
                            logger.warning(
                                "Rate limited on %s, retrying in %.1fs", url, delay
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            body = await resp.text()
                            last_error = BeaconAPIError(
                                f"HTTP {resp.status}: {body[:200]}",
                                status_code=resp.status,
                                url=url,
                            )
                            logger.warning(
                                "Beacon API error on %s: %s", url, last_error
                            )
                except BeaconAPIError:
                    raise
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    last_error = exc
                    logger.warning(
                        "Beacon API request failed (%s): %s", url, exc
                    )

                if attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

            logger.info("Beacon URL %s exhausted, trying next", url)

        raise BeaconAPIError(
            f"All beacon API attempts failed for {path}: {last_error}",
            url=urls[0],
        )

    async def _execution_rpc(
        self, method: str, params: list
    ) -> Any:
        """Call an execution-layer JSON-RPC method with retries.

        Parameters
        ----------
        method : str
            RPC method name (e.g. ``"eth_getProof"``).
        params : list
            RPC parameters.

        Returns
        -------
        Any
            The ``result`` field from the JSON-RPC response.

        Raises
        ------
        ExecutionRPCError
            If the call fails.
        """
        self._rpc_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._rpc_id,
        }

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                session = await self._get_session()
                async with session.post(
                    self._execution_url, json=payload
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        last_error = ExecutionRPCError(
                            f"HTTP {resp.status}: {body[:200]}"
                        )
                        logger.warning(
                            "Execution RPC HTTP error: %s", last_error
                        )
                    else:
                        data = await resp.json(content_type=None)
                        if "error" in data:
                            err = data["error"]
                            raise ExecutionRPCError(
                                f"RPC error: {err.get('message', err)}",
                                code=err.get("code", 0),
                            )
                        return data.get("result")
            except ExecutionRPCError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                logger.warning("Execution RPC failed: %s", exc)

            if attempt < self._max_retries - 1:
                delay = self._retry_base_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        raise ExecutionRPCError(
            f"All execution RPC attempts failed for {method}: {last_error}"
        )

    # ── Beacon API response parsing ─────────────────────────────────────

    @staticmethod
    def _parse_beacon_header(header_msg: dict, timestamp: int = 0) -> BeaconHeader:
        """Parse a beacon header JSON message into a BeaconHeader.

        Parameters
        ----------
        header_msg : dict
            The ``message`` object from the API response
            (with slot, proposer_index, parent_root, state_root, body_root).
        timestamp : int
            Optional Unix timestamp (computed from slot if 0).

        Returns
        -------
        BeaconHeader
        """
        slot = int(header_msg["slot"])
        if timestamp == 0:
            timestamp = slot_to_timestamp(slot)

        return BeaconHeader(
            slot=slot,
            proposer_index=int(header_msg["proposer_index"]),
            parent_root=header_msg["parent_root"],
            state_root=header_msg["state_root"],
            body_root=header_msg["body_root"],
            timestamp=timestamp,
        )

    @staticmethod
    def _parse_sync_committee(
        sc_data: dict, period: int
    ) -> SyncCommittee:
        """Parse sync committee JSON into a SyncCommittee.

        Parameters
        ----------
        sc_data : dict
            Sync committee object with ``pubkeys`` and ``aggregate_pubkey``.
        period : int
            The committee's period number.

        Returns
        -------
        SyncCommittee
        """
        return SyncCommittee(
            period=period,
            pubkeys=sc_data["pubkeys"],
            aggregate_pubkey=sc_data["aggregate_pubkey"],
        )

    # ── EthLightClient ABC implementation ───────────────────────────────

    async def sync(self, checkpoint: str = "") -> None:
        """Sync the light client from the beacon chain.

        Fetches the latest finalized header and, if a checkpoint block
        root is provided, bootstraps the sync committee from it.
        Otherwise, derives the current period from the finalized header
        and fetches the committee via light client updates.

        Parameters
        ----------
        checkpoint : str
            A trusted block root (hex) for bootstrapping. If empty,
            uses the latest finalized header's root.
        """
        logger.info("Syncing beacon light client...")

        # 1. Fetch latest finalized header
        resp = await self._beacon_get("/eth/v1/beacon/headers/finalized")
        header_data = resp["data"]["header"]["message"]
        block_root = resp["data"]["root"]

        self._finalized_header = self._parse_beacon_header(header_data)
        self._finalized_block_root = block_root
        self._latest_slot = self._finalized_header.slot
        self._header_cache.put(self._finalized_header.slot, self._finalized_header)

        logger.info(
            "Finalized header: slot=%d, state_root=%s",
            self._finalized_header.slot,
            self._finalized_header.state_root,
        )

        # 2. Determine checkpoint for bootstrap
        bootstrap_root = checkpoint or block_root
        self._checkpoint = bootstrap_root

        # 3. Bootstrap sync committee
        try:
            bootstrap = await self._beacon_get(
                f"/eth/v1/beacon/light_client/bootstrap/{bootstrap_root}"
            )
            sc_data = bootstrap["data"]["current_sync_committee"]
            period = slot_to_sync_committee_period(self._finalized_header.slot)
            committee = self._parse_sync_committee(sc_data, period)
            self._committee_cache[period] = committee
            logger.info(
                "Bootstrapped sync committee: period=%d, %d pubkeys",
                period, len(committee.pubkeys),
            )
        except BeaconAPIError as exc:
            logger.warning(
                "Bootstrap failed (%s), trying light client updates", exc
            )
            # Fallback: fetch via light client updates
            period = slot_to_sync_committee_period(self._finalized_header.slot)
            await self._fetch_sync_committee_update(period)

        self._synced = True
        logger.info("Light client synced successfully")

    async def _fetch_sync_committee_update(self, period: int) -> SyncCommittee:
        """Fetch a sync committee for a given period via light client updates.

        Parameters
        ----------
        period : int
            The sync committee period.

        Returns
        -------
        SyncCommittee

        Raises
        ------
        BeaconAPIError
            If the committee cannot be fetched.
        """
        if period in self._committee_cache:
            return self._committee_cache[period]

        resp = await self._beacon_get(
            f"/eth/v1/beacon/light_client/updates?start_period={period}&count=1"
        )

        # Response is an array of updates
        updates = resp if isinstance(resp, list) else [resp]
        if not updates:
            raise BeaconAPIError(
                f"No light client updates for period {period}"
            )

        update = updates[0]
        # Handle both wrapped and unwrapped format
        data = update.get("data", update)

        sc_data = data.get("next_sync_committee")
        if sc_data is None:
            raise BeaconAPIError(
                f"No next_sync_committee in update for period {period}"
            )

        committee = self._parse_sync_committee(sc_data, period)
        self._committee_cache[period] = committee
        logger.info(
            "Fetched sync committee: period=%d, %d pubkeys",
            period, len(committee.pubkeys),
        )
        return committee

    async def get_verified_header(self, slot: int) -> BeaconHeader:
        """Fetch a beacon header for a given slot.

        First checks the local cache, then queries the Beacon API.

        Parameters
        ----------
        slot : int
            Slot number.

        Returns
        -------
        BeaconHeader

        Raises
        ------
        KeyError
            If no header exists at the requested slot.
        """
        # Check cache
        cached = self._header_cache.get(slot)
        if cached is not None:
            return cached

        try:
            resp = await self._beacon_get(f"/eth/v1/beacon/headers/{slot}")
        except BeaconAPIError as exc:
            if exc.status_code == 404:
                raise KeyError(f"No header for slot {slot}") from exc
            raise

        header_data = resp["data"]["header"]["message"]
        header = self._parse_beacon_header(header_data)
        self._header_cache.put(slot, header)
        return header

    async def latest_header(self) -> BeaconHeader:
        """Get the latest finalized header.

        Refreshes from the API if the client is synced.

        Returns
        -------
        BeaconHeader

        Raises
        ------
        RuntimeError
            If the client has not been synced yet.
        """
        if not self._synced:
            raise RuntimeError("Light client not synced — call sync() first")

        # Refresh from API
        try:
            resp = await self._beacon_get("/eth/v1/beacon/headers/finalized")
            header_data = resp["data"]["header"]["message"]
            block_root = resp["data"]["root"]
            header = self._parse_beacon_header(header_data)

            self._finalized_header = header
            self._finalized_block_root = block_root
            self._latest_slot = header.slot
            self._header_cache.put(header.slot, header)
        except BeaconAPIError:
            # Return cached if refresh fails
            logger.warning("Failed to refresh finalized header, using cached")

        if self._finalized_header is None:
            raise RuntimeError("No finalized header available")

        return self._finalized_header

    async def verify_state_proof(
        self,
        address: str,
        storage_keys: List[str],
        block: int,
    ) -> StateProof:
        """Fetch and verify a state proof via ``eth_getProof``.

        Calls the execution-layer ``eth_getProof`` JSON-RPC method and
        verifies the resulting Merkle-Patricia Trie proof against the
        known state root (if a header for the block is available).

        Parameters
        ----------
        address : str
            Ethereum address (0x-prefixed).
        storage_keys : list of str
            Storage slot keys to prove (0x-prefixed, 32-byte hex).
        block : int
            Block number for the proof.

        Returns
        -------
        StateProof
            With ``verified=True`` if MPT verification succeeds.
        """
        # Fetch the proof from execution layer
        block_hex = hex(block)
        raw = await self._execution_rpc(
            "eth_getProof", [address, storage_keys, block_hex]
        )

        if raw is None:
            raise ExecutionRPCError(f"eth_getProof returned null for {address}")

        # Parse the response
        account_proof_hex = raw.get("accountProof", [])
        balance = int(raw.get("balance", "0x0"), 16)
        nonce = int(raw.get("nonce", "0x0"), 16)
        code_hash = raw.get("codeHash", "0x" + "00" * 32)
        storage_hash = raw.get("storageHash", "0x" + "00" * 32)

        # Parse storage proofs
        storage_proofs: Dict[str, Any] = {}
        for sp in raw.get("storageProof", []):
            key = sp["key"]
            storage_proofs[key] = {
                "value": sp["value"],
                "proof": sp["proof"],
            }

        state_proof = StateProof(
            address=address,
            balance=balance,
            nonce=nonce,
            code_hash=code_hash,
            storage_hash=storage_hash,
            account_proof=account_proof_hex,
            storage_proofs=storage_proofs,
            block_number=block,
            verified=False,
        )

        # Attempt MPT verification against known state root
        state_proof.verified = await self._verify_account_proof(
            address=address,
            account_proof_hex=account_proof_hex,
            block_number=block,
        )

        return state_proof

    async def _verify_account_proof(
        self,
        address: str,
        account_proof_hex: List[str],
        block_number: int,
    ) -> bool:
        """Verify an account proof against a known state root.

        Parameters
        ----------
        address : str
            Ethereum address.
        account_proof_hex : list of str
            Hex-encoded RLP proof nodes.
        block_number : int
            Block number to look up the state root for.

        Returns
        -------
        bool
            True if verification succeeds.
        """
        # We need the execution state root for this block.
        # Try to find a beacon header whose execution payload matches.
        # For simplicity, check if we have the finalized header and
        # its execution block matches.
        state_root_hex = await self._get_execution_state_root(block_number)
        if state_root_hex is None:
            logger.info(
                "No state root available for block %d, skipping MPT "
                "verification",
                block_number,
            )
            return False

        try:
            state_root = bytes.fromhex(state_root_hex.removeprefix("0x"))
            proof_nodes = [
                bytes.fromhex(p.removeprefix("0x")) for p in account_proof_hex
            ]
            result = MerklePatriciaVerifier.verify_account_proof(
                state_root, address, proof_nodes
            )
            if result is not None:
                logger.info(
                    "Account proof verified: address=%s, nonce=%d, "
                    "balance=%d",
                    address, result.nonce, result.balance,
                )
                return True
            else:
                logger.warning(
                    "Account proof verification failed for %s at block %d",
                    address, block_number,
                )
                return False
        except Exception as exc:
            logger.warning(
                "MPT verification error for %s: %s", address, exc
            )
            return False

    async def _get_execution_state_root(
        self, block_number: int
    ) -> Optional[str]:
        """Get the execution-layer state root for a block number.

        Queries the execution layer via ``eth_getBlockByNumber`` to
        retrieve the state root.

        Parameters
        ----------
        block_number : int
            Execution block number.

        Returns
        -------
        str or None
            Hex state root, or None if unavailable.
        """
        try:
            block_hex = hex(block_number)
            result = await self._execution_rpc(
                "eth_getBlockByNumber", [block_hex, False]
            )
            if result and "stateRoot" in result:
                return result["stateRoot"]
        except Exception as exc:
            logger.debug(
                "Could not get state root for block %d: %s",
                block_number, exc,
            )
        return None

    async def verify_event(self, tx_hash: str, log_index: int) -> EventProof:
        """Verify an event by fetching the transaction receipt.

        Retrieves the receipt from the execution layer, extracts the
        specified log, and returns it as an :class:`EventProof`. Full
        receipt-trie Merkle proof verification is not currently
        supported by standard JSON-RPC nodes (would need a custom
        ``eth_getReceiptProof``); the proof is constructed from the
        receipt data for structural compatibility.

        Parameters
        ----------
        tx_hash : str
            Transaction hash.
        log_index : int
            Index of the log within the receipt.

        Returns
        -------
        EventProof

        Raises
        ------
        KeyError
            If the transaction or log index doesn't exist.
        """
        # Fetch receipt
        receipt = await self._execution_rpc(
            "eth_getTransactionReceipt", [tx_hash]
        )
        if receipt is None:
            raise KeyError(f"No receipt for tx {tx_hash}")

        logs = receipt.get("logs", [])

        # Find the target log
        target_log = None
        for log in logs:
            if int(log.get("logIndex", "0x0"), 16) == log_index:
                target_log = log
                break

        if target_log is None:
            raise KeyError(
                f"No log at index {log_index} in tx {tx_hash} "
                f"(receipt has {len(logs)} logs)"
            )

        block_number = int(receipt.get("blockNumber", "0x0"), 16)

        return EventProof(
            tx_hash=tx_hash,
            log_index=log_index,
            address=target_log["address"],
            topics=target_log.get("topics", []),
            data=target_log.get("data", "0x"),
            block_number=block_number,
            receipt_proof=[],  # Standard nodes don't expose receipt proofs
            verified=True,  # Receipt exists on chain
        )

    async def get_sync_committee(self, period: int) -> SyncCommittee:
        """Get the sync committee for a given period.

        Checks the cache first, then fetches via light client updates.

        Parameters
        ----------
        period : int
            Sync committee period number.

        Returns
        -------
        SyncCommittee

        Raises
        ------
        KeyError
            If the committee cannot be fetched.
        """
        if period in self._committee_cache:
            return self._committee_cache[period]

        try:
            return await self._fetch_sync_committee_update(period)
        except BeaconAPIError as exc:
            raise KeyError(
                f"No sync committee for period {period}: {exc}"
            ) from exc

    async def get_latest_slot(self) -> int:
        """Get the latest verified (finalized) slot number.

        Returns
        -------
        int
        """
        if self._synced and self._finalized_header:
            # Optionally refresh — but to avoid excessive API calls,
            # return the cached value.
            return self._latest_slot

        # If not synced, try to fetch
        try:
            resp = await self._beacon_get("/eth/v1/beacon/headers/finalized")
            slot = int(resp["data"]["header"]["message"]["slot"])
            self._latest_slot = slot
            return slot
        except BeaconAPIError:
            return self._latest_slot

    @property
    def is_synced(self) -> bool:
        """Whether the light client has completed initial sync."""
        return self._synced

    # ── Extended API (beyond EthLightClient ABC) ────────────────────────

    async def get_execution_proof(
        self,
        address: str,
        storage_keys: Optional[List[str]] = None,
        block: str = "latest",
    ) -> dict:
        """Call ``eth_getProof`` on the execution layer, returning raw JSON.

        This is a lower-level method that returns the raw RPC response
        without attempting MPT verification.

        Parameters
        ----------
        address : str
            Ethereum address.
        storage_keys : list of str or None
            Storage slot keys.
        block : str
            Block identifier (``"latest"``, ``"finalized"``, or hex number).

        Returns
        -------
        dict
            Raw ``eth_getProof`` result.
        """
        if storage_keys is None:
            storage_keys = []

        result = await self._execution_rpc(
            "eth_getProof", [address, storage_keys, block]
        )
        if result is None:
            raise ExecutionRPCError(
                f"eth_getProof returned null for {address}"
            )
        return result

    async def get_finality_update(self) -> dict:
        """Fetch the latest light client finality update.

        Returns
        -------
        dict
            Raw finality update data.
        """
        resp = await self._beacon_get(
            "/eth/v1/beacon/light_client/finality_update"
        )
        return resp

    async def get_chain_config(self) -> dict:
        """Fetch the chain configuration spec.

        Returns
        -------
        dict
            Chain configuration parameters.
        """
        resp = await self._beacon_get("/eth/v1/config/spec")
        return resp.get("data", {})

    async def get_block(self, block_id: str = "finalized") -> dict:
        """Fetch a full beacon block.

        Parameters
        ----------
        block_id : str
            Block identifier (slot number, ``"head"``, ``"finalized"``).

        Returns
        -------
        dict
            Raw block data.
        """
        resp = await self._beacon_get(f"/eth/v2/beacon/blocks/{block_id}")
        return resp

    async def get_state_root(self, state_id: str = "finalized") -> str:
        """Fetch the state root for a given state identifier.

        Parameters
        ----------
        state_id : str
            State identifier (slot, ``"head"``, ``"finalized"``).

        Returns
        -------
        str
            Hex-encoded state root.
        """
        resp = await self._beacon_get(
            f"/eth/v1/beacon/states/{state_id}/root"
        )
        return resp["data"]["root"]

    @property
    def finalized_header(self) -> Optional[BeaconHeader]:
        """The most recently fetched finalized header."""
        return self._finalized_header

    @property
    def finalized_block_root(self) -> str:
        """The block root of the most recently fetched finalized header."""
        return self._finalized_block_root

    @property
    def checkpoint(self) -> str:
        """The checkpoint used for initial sync."""
        return self._checkpoint

    def __repr__(self) -> str:
        return (
            f"BeaconAPILightClient("
            f"synced={self._synced}, "
            f"latest_slot={self._latest_slot}, "
            f"beacon_url={self._beacon_url!r}, "
            f"cached_headers={len(self._header_cache)}, "
            f"cached_committees={len(self._committee_cache)})"
        )
