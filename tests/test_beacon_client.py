"""
Tests for BeaconAPILightClient
===============================

Two test categories:

1. **Unit tests** — mock all HTTP calls with ``aiohttp`` test utilities.
   Run in CI without network access.
2. **Network tests** — hit real Sepolia Beacon API endpoints.
   Marked with ``@pytest.mark.network`` and skipped by default.
   Run with: ``pytest -m network tests/test_beacon_client.py``

Covers:
- Session management (create / close / context manager)
- Beacon API GET with retries, fallback, rate-limit handling
- Execution JSON-RPC with retries
- Header parsing and caching
- Sync committee parsing and caching
- Full sync() flow (bootstrap + fallback)
- get_verified_header (cache hit + API fetch + 404)
- latest_header (refresh + cached fallback)
- verify_state_proof + MPT verification
- verify_event (receipt lookup)
- get_sync_committee (cache + fetch)
- get_latest_slot (synced + unsynced)
- Extended API: get_execution_proof, get_finality_update, get_chain_config
- LRU cache behaviour
- Helper functions (slot_to_epoch, slot_to_timestamp, etc.)
- Network integration tests against real Sepolia endpoints
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Ensure project root is on sys.path ──────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_src = os.path.join(os.path.dirname(_here), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from asi_build.rings.bridge.beacon_client import (
    DEFAULT_HEADER_CACHE_SIZE,
    EPOCHS_PER_SYNC_COMMITTEE_PERIOD,
    SEPOLIA_GENESIS_TIME,
    SLOTS_PER_EPOCH,
    SLOTS_PER_SYNC_COMMITTEE_PERIOD,
    BeaconAPIError,
    BeaconAPILightClient,
    ExecutionRPCError,
    LRUCache,
    epoch_to_sync_committee_period,
    slot_to_epoch,
    slot_to_sync_committee_period,
    slot_to_timestamp,
)
from asi_build.rings.bridge.light_client import (
    BeaconHeader,
    EthLightClient,
    StateProof,
    SyncCommittee,
)
from asi_build.rings.bridge.merkle_patricia import MerklePatriciaVerifier

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

# Sample data mimicking real Sepolia API responses

SAMPLE_FINALIZED_HEADER_RESP = {
    "execution_optimistic": False,
    "finalized": True,
    "data": {
        "root": "0x944c99732fdf3de8201f0a4aeddc3847aa5f3a3d43598d97ebbd9a74b917a8df",
        "canonical": True,
        "header": {
            "message": {
                "slot": "10022528",
                "proposer_index": "512",
                "parent_root": "0x539b1b69a5a897e264390a80d40ddfad988c832db6b225c8abac24bf3fe4430d",
                "state_root": "0x46166af871046f6f47837f3e045adf8e067650188df5cb727c3fa1f594077da4",
                "body_root": "0xa4d7db20e66cfdfeb7a76598d2104985633dcfc32876b8a78c0217f124dde9ec",
            },
            "signature": "0xae768f1cc649df90e2c242b016665150f74fb85327387c9cbe0b876c909046b3",
        },
    },
}

SAMPLE_BOOTSTRAP_RESP = {
    "version": "fulu",
    "data": {
        "header": {
            "beacon": {
                "slot": "10022528",
                "proposer_index": "512",
                "parent_root": "0x539b1b69",
                "state_root": "0x46166af8",
                "body_root": "0xa4d7db20",
            },
        },
        "current_sync_committee": {
            "pubkeys": [f"0x{'aa' * 48}" for _ in range(512)],
            "aggregate_pubkey": "0x" + "bb" * 48,
        },
    },
}

SAMPLE_LC_UPDATES_RESP = [
    {
        "version": "fulu",
        "data": {
            "attested_header": {
                "beacon": {
                    "slot": "10002735",
                    "proposer_index": "428",
                    "parent_root": "0x6a014fe1",
                    "state_root": "0x624cf96b",
                    "body_root": "0x6a69f6a7",
                },
            },
            "next_sync_committee": {
                "pubkeys": [f"0x{'cc' * 48}" for _ in range(512)],
                "aggregate_pubkey": "0x" + "dd" * 48,
            },
        },
    }
]

SAMPLE_ETH_GET_PROOF = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "address": "0xe034d479edc2530d9917dda4547b59bf0964a2ca",
        "accountProof": [
            "0xf90211a0b67f5a11679a6b705e95a051ec43868f",
            "0xf90211a0a463880feb4d4bafed3556ceecf96646",
        ],
        "balance": "0x38d7ea4c68000",
        "codeHash": "0x34ebaa6458750075bfc7f0cf9a1a90e949348ea7c82c2d38acd276402c4caabc",
        "nonce": "0x1",
        "storageHash": "0x82bbc027aa0ae8e310a4207921c938e8fd1855fbfb38abf1406f9d5734e9b110",
        "storageProof": [],
    },
}

SAMPLE_TX_RECEIPT = {
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "blockNumber": "0xa27c71",
        "logs": [
            {
                "logIndex": "0x0",
                "address": "0xe034d479edc2530d9917dda4547b59bf0964a2ca",
                "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"],
                "data": "0x0000000000000000000000000000000000000000000000000de0b6b3a7640000",
            },
            {
                "logIndex": "0x1",
                "address": "0xe034d479edc2530d9917dda4547b59bf0964a2ca",
                "topics": ["0xabcdef"],
                "data": "0x1234",
            },
        ],
    },
}


class FakeResponse:
    """Minimal mock for aiohttp.ClientResponse."""

    def __init__(self, status: int, data: Any, text: str = "") -> None:
        self.status = status
        self._data = data
        self._text = text or json.dumps(data) if isinstance(data, dict) else text

    async def json(self, content_type: Any = None) -> Any:
        return self._data

    async def text(self) -> str:
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeSession:
    """Minimal mock for aiohttp.ClientSession."""

    def __init__(self) -> None:
        self.closed = False
        self._get_responses: List[FakeResponse] = []
        self._post_responses: List[FakeResponse] = []
        self._get_call_count = 0
        self._post_call_count = 0

    def set_get_responses(self, responses: List[FakeResponse]) -> None:
        self._get_responses = responses

    def set_post_responses(self, responses: List[FakeResponse]) -> None:
        self._post_responses = responses

    def get(self, url: str, **kwargs) -> FakeResponse:
        idx = min(self._get_call_count, len(self._get_responses) - 1)
        self._get_call_count += 1
        return self._get_responses[idx]

    def post(self, url: str, **kwargs) -> FakeResponse:
        idx = min(self._post_call_count, len(self._post_responses) - 1)
        self._post_call_count += 1
        return self._post_responses[idx]

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def client() -> BeaconAPILightClient:
    """Create a client with short timeouts for testing."""
    return BeaconAPILightClient(
        beacon_url="https://test-beacon.example.com",
        execution_url="https://test-execution.example.com",
        fallback_beacon_url=None,
        timeout=5.0,
        max_retries=1,
        retry_base_delay=0.01,
    )


@pytest.fixture
def client_with_fallback() -> BeaconAPILightClient:
    """Create a client with a fallback URL."""
    return BeaconAPILightClient(
        beacon_url="https://test-beacon.example.com",
        execution_url="https://test-execution.example.com",
        fallback_beacon_url="https://fallback-beacon.example.com",
        timeout=5.0,
        max_retries=1,
        retry_base_delay=0.01,
    )


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_slot_to_epoch(self):
        assert slot_to_epoch(0) == 0
        assert slot_to_epoch(31) == 0
        assert slot_to_epoch(32) == 1
        assert slot_to_epoch(10022528) == 313204

    def test_epoch_to_sync_committee_period(self):
        assert epoch_to_sync_committee_period(0) == 0
        assert epoch_to_sync_committee_period(255) == 0
        assert epoch_to_sync_committee_period(256) == 1
        assert epoch_to_sync_committee_period(313204) == 1223

    def test_slot_to_sync_committee_period(self):
        # slot 10022528 → epoch 313204 → period 1223
        assert slot_to_sync_committee_period(10022528) == 1223
        assert slot_to_sync_committee_period(0) == 0

    def test_slot_to_timestamp(self):
        ts = slot_to_timestamp(0)
        assert ts == SEPOLIA_GENESIS_TIME
        ts = slot_to_timestamp(1)
        assert ts == SEPOLIA_GENESIS_TIME + 12
        ts = slot_to_timestamp(100, genesis_time=0)
        assert ts == 1200


# ---------------------------------------------------------------------------
# LRU Cache tests
# ---------------------------------------------------------------------------


class TestLRUCache:
    """Tests for the LRU cache implementation."""

    def test_basic_put_get(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") is None

    def test_eviction(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # Should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_order(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        # Access "a" to make it recently used
        cache.get("a")
        cache.put("c", 3)  # Should evict "b", not "a"
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_update_existing(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("a", 10)
        assert cache.get("a") == 10
        assert len(cache) == 1

    def test_contains(self):
        cache = LRUCache(max_size=3)
        cache.put("x", 42)
        assert "x" in cache
        assert "y" not in cache

    def test_clear(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert len(cache) == 0
        assert cache.get("a") is None

    def test_large_cache(self):
        cache = LRUCache(max_size=1000)
        for i in range(1000):
            cache.put(i, i * 10)
        assert len(cache) == 1000
        assert cache.get(0) == 0
        assert cache.get(999) == 9990


# ---------------------------------------------------------------------------
# Client instantiation tests
# ---------------------------------------------------------------------------


class TestClientInit:
    """Tests for BeaconAPILightClient initialization."""

    def test_default_init(self):
        c = BeaconAPILightClient()
        assert not c.is_synced
        assert c._beacon_url == "https://ethereum-sepolia-beacon-api.publicnode.com"
        assert c._execution_url == "https://ethereum-sepolia-rpc.publicnode.com"
        assert c._fallback_beacon_url == "https://lodestar-sepolia.chainsafe.io"

    def test_custom_init(self, client):
        assert client._beacon_url == "https://test-beacon.example.com"
        assert client._fallback_beacon_url is None
        assert not client.is_synced

    def test_trailing_slash_stripped(self):
        c = BeaconAPILightClient(
            beacon_url="https://example.com/",
            execution_url="https://exec.com/",
            fallback_beacon_url="https://fallback.com/",
        )
        assert c._beacon_url == "https://example.com"
        assert c._execution_url == "https://exec.com"
        assert c._fallback_beacon_url == "https://fallback.com"

    def test_no_fallback(self):
        c = BeaconAPILightClient(fallback_beacon_url=None)
        assert c._fallback_beacon_url is None

    def test_implements_abc(self, client):
        assert isinstance(client, EthLightClient)

    def test_repr(self, client):
        r = repr(client)
        assert "BeaconAPILightClient" in r
        assert "synced=False" in r


# ---------------------------------------------------------------------------
# Session management tests
# ---------------------------------------------------------------------------


class TestSessionManagement:
    """Tests for session creation and cleanup."""

    @pytest.mark.asyncio
    async def test_get_session_creates_session(self, client):
        session = await client._get_session()
        assert session is not None
        await client.close()

    @pytest.mark.asyncio
    async def test_close_session(self, client):
        await client._get_session()
        await client.close()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with BeaconAPILightClient(
            beacon_url="https://test.com",
            execution_url="https://test.com",
            fallback_beacon_url=None,
        ) as client:
            assert client is not None
        # Session should be closed after context exit

    @pytest.mark.asyncio
    async def test_close_when_no_session(self, client):
        # Should not raise
        await client.close()


# ---------------------------------------------------------------------------
# Beacon API GET tests (mocked)
# ---------------------------------------------------------------------------


class TestBeaconGet:
    """Tests for _beacon_get with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_successful_get(self, client):
        fake = FakeSession()
        fake.set_get_responses([FakeResponse(200, {"data": "test"})])
        client._session = fake

        result = await client._beacon_get("/test")
        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_404_raises_error(self, client):
        fake = FakeSession()
        fake.set_get_responses([FakeResponse(404, {}, "Not found")])
        client._session = fake

        with pytest.raises(BeaconAPIError) as exc_info:
            await client._beacon_get("/missing")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_500_retries_then_fails(self, client):
        fake = FakeSession()
        fake.set_get_responses([FakeResponse(500, {}, "Server error")])
        client._session = fake
        client._max_retries = 2
        client._retry_base_delay = 0.001

        with pytest.raises(BeaconAPIError):
            await client._beacon_get("/failing", use_fallback=False)

    @pytest.mark.asyncio
    async def test_fallback_url(self, client_with_fallback):
        fake = FakeSession()
        # Primary fails, fallback succeeds
        fake.set_get_responses([
            FakeResponse(500, {}, "Primary down"),
            FakeResponse(200, {"data": "from_fallback"}),
        ])
        client_with_fallback._session = fake
        client_with_fallback._retry_base_delay = 0.001

        result = await client_with_fallback._beacon_get("/test")
        assert result == {"data": "from_fallback"}


# ---------------------------------------------------------------------------
# Execution RPC tests (mocked)
# ---------------------------------------------------------------------------


class TestExecutionRPC:
    """Tests for _execution_rpc with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_successful_rpc(self, client):
        fake = FakeSession()
        fake.set_post_responses([
            FakeResponse(200, {"jsonrpc": "2.0", "id": 1, "result": "0x1234"})
        ])
        client._session = fake

        result = await client._execution_rpc("eth_blockNumber", [])
        assert result == "0x1234"

    @pytest.mark.asyncio
    async def test_rpc_error(self, client):
        fake = FakeSession()
        fake.set_post_responses([
            FakeResponse(200, {
                "jsonrpc": "2.0", "id": 1,
                "error": {"code": -32600, "message": "Invalid request"},
            })
        ])
        client._session = fake

        with pytest.raises(ExecutionRPCError) as exc_info:
            await client._execution_rpc("bad_method", [])
        assert exc_info.value.code == -32600

    @pytest.mark.asyncio
    async def test_rpc_http_error(self, client):
        fake = FakeSession()
        fake.set_post_responses([FakeResponse(503, {}, "Service unavailable")])
        client._session = fake
        client._retry_base_delay = 0.001

        with pytest.raises(ExecutionRPCError):
            await client._execution_rpc("eth_test", [])


# ---------------------------------------------------------------------------
# Header parsing tests
# ---------------------------------------------------------------------------


class TestHeaderParsing:

    def test_parse_beacon_header(self):
        msg = SAMPLE_FINALIZED_HEADER_RESP["data"]["header"]["message"]
        header = BeaconAPILightClient._parse_beacon_header(msg)
        assert header.slot == 10022528
        assert header.proposer_index == 512
        assert header.parent_root == "0x539b1b69a5a897e264390a80d40ddfad988c832db6b225c8abac24bf3fe4430d"
        assert header.state_root == "0x46166af871046f6f47837f3e045adf8e067650188df5cb727c3fa1f594077da4"
        assert header.body_root == "0xa4d7db20e66cfdfeb7a76598d2104985633dcfc32876b8a78c0217f124dde9ec"
        assert header.timestamp == slot_to_timestamp(10022528)

    def test_parse_beacon_header_with_timestamp(self):
        msg = {"slot": "100", "proposer_index": "5", "parent_root": "0xaa",
               "state_root": "0xbb", "body_root": "0xcc"}
        header = BeaconAPILightClient._parse_beacon_header(msg, timestamp=9999)
        assert header.timestamp == 9999

    def test_parse_sync_committee(self):
        sc_data = SAMPLE_BOOTSTRAP_RESP["data"]["current_sync_committee"]
        committee = BeaconAPILightClient._parse_sync_committee(sc_data, period=1223)
        assert committee.period == 1223
        assert len(committee.pubkeys) == 512
        assert committee.aggregate_pubkey == "0x" + "bb" * 48


# ---------------------------------------------------------------------------
# Sync tests (mocked)
# ---------------------------------------------------------------------------


class TestSync:
    """Tests for the sync() method."""

    @pytest.mark.asyncio
    async def test_sync_with_bootstrap(self, client):
        call_idx = [0]
        responses = [
            SAMPLE_FINALIZED_HEADER_RESP,  # finalized header
            SAMPLE_BOOTSTRAP_RESP,  # bootstrap
        ]

        async def mock_get(path, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            return responses[idx]

        client._beacon_get = mock_get

        await client.sync()
        assert client.is_synced
        assert client._latest_slot == 10022528
        assert client._finalized_header is not None
        assert client._finalized_header.slot == 10022528
        assert 1223 in client._committee_cache

    @pytest.mark.asyncio
    async def test_sync_bootstrap_fallback_to_updates(self, client):
        call_idx = [0]

        async def mock_get(path, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return SAMPLE_FINALIZED_HEADER_RESP
            elif idx == 1:
                # Bootstrap fails
                raise BeaconAPIError("Bootstrap not found", status_code=404)
            else:
                # Light client updates
                return SAMPLE_LC_UPDATES_RESP

        client._beacon_get = mock_get

        await client.sync()
        assert client.is_synced
        assert 1223 in client._committee_cache

    @pytest.mark.asyncio
    async def test_sync_with_explicit_checkpoint(self, client):
        call_idx = [0]
        checkpoint = "0xdeadbeef"

        async def mock_get(path, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return SAMPLE_FINALIZED_HEADER_RESP
            elif idx == 1:
                # Verify the checkpoint is used in the bootstrap URL
                assert checkpoint in path
                return SAMPLE_BOOTSTRAP_RESP

        client._beacon_get = mock_get

        await client.sync(checkpoint=checkpoint)
        assert client.checkpoint == checkpoint


# ---------------------------------------------------------------------------
# get_verified_header tests
# ---------------------------------------------------------------------------


class TestGetVerifiedHeader:

    @pytest.mark.asyncio
    async def test_cache_hit(self, client):
        header = BeaconHeader(
            slot=100, proposer_index=5,
            parent_root="0xaa", state_root="0xbb",
            body_root="0xcc", timestamp=1234,
        )
        client._header_cache.put(100, header)

        result = await client.get_verified_header(100)
        assert result.slot == 100
        assert result.timestamp == 1234

    @pytest.mark.asyncio
    async def test_api_fetch(self, client):
        async def mock_get(path, **kwargs):
            return SAMPLE_FINALIZED_HEADER_RESP

        client._beacon_get = mock_get
        result = await client.get_verified_header(10022528)
        assert result.slot == 10022528
        # Should be cached now
        assert client._header_cache.get(10022528) is not None

    @pytest.mark.asyncio
    async def test_404_raises_key_error(self, client):
        async def mock_get(path, **kwargs):
            raise BeaconAPIError("Not found", status_code=404)

        client._beacon_get = mock_get
        with pytest.raises(KeyError, match="No header for slot 999"):
            await client.get_verified_header(999)

    @pytest.mark.asyncio
    async def test_other_error_propagates(self, client):
        async def mock_get(path, **kwargs):
            raise BeaconAPIError("Server error", status_code=500)

        client._beacon_get = mock_get
        with pytest.raises(BeaconAPIError):
            await client.get_verified_header(999)


# ---------------------------------------------------------------------------
# latest_header tests
# ---------------------------------------------------------------------------


class TestLatestHeader:

    @pytest.mark.asyncio
    async def test_not_synced_raises(self, client):
        with pytest.raises(RuntimeError, match="not synced"):
            await client.latest_header()

    @pytest.mark.asyncio
    async def test_refreshes_from_api(self, client):
        client._synced = True
        client._finalized_header = BeaconHeader(
            slot=100, proposer_index=1,
            parent_root="0x", state_root="0x",
            body_root="0x",
        )

        async def mock_get(path, **kwargs):
            return SAMPLE_FINALIZED_HEADER_RESP

        client._beacon_get = mock_get
        result = await client.latest_header()
        assert result.slot == 10022528

    @pytest.mark.asyncio
    async def test_uses_cached_on_failure(self, client):
        client._synced = True
        cached = BeaconHeader(
            slot=100, proposer_index=1,
            parent_root="0x", state_root="0x",
            body_root="0x",
        )
        client._finalized_header = cached

        async def mock_get(path, **kwargs):
            raise BeaconAPIError("Failed")

        client._beacon_get = mock_get
        result = await client.latest_header()
        assert result.slot == 100


# ---------------------------------------------------------------------------
# verify_state_proof tests
# ---------------------------------------------------------------------------


class TestVerifyStateProof:

    @pytest.mark.asyncio
    async def test_basic_state_proof(self, client):
        async def mock_rpc(method, params):
            if method == "eth_getProof":
                return SAMPLE_ETH_GET_PROOF["result"]
            elif method == "eth_getBlockByNumber":
                return None  # No state root available
            return None

        client._execution_rpc = mock_rpc

        proof = await client.verify_state_proof(
            "0xe034d479edc2530d9917dda4547b59bf0964a2ca",
            [],
            block=10644593,
        )
        assert proof.address == "0xe034d479edc2530d9917dda4547b59bf0964a2ca"
        assert proof.balance == 0x38d7ea4c68000
        assert proof.nonce == 1
        assert proof.block_number == 10644593
        # Verification skipped since we can't get state root
        assert proof.verified is False

    @pytest.mark.asyncio
    async def test_state_proof_null_result(self, client):
        async def mock_rpc(method, params):
            return None

        client._execution_rpc = mock_rpc

        with pytest.raises(ExecutionRPCError, match="null"):
            await client.verify_state_proof("0xabc", [], block=1)


# ---------------------------------------------------------------------------
# verify_event tests
# ---------------------------------------------------------------------------


class TestVerifyEvent:

    @pytest.mark.asyncio
    async def test_verify_event_found(self, client):
        async def mock_rpc(method, params):
            return SAMPLE_TX_RECEIPT["result"]

        client._execution_rpc = mock_rpc

        proof = await client.verify_event("0xtxhash", 0)
        assert proof.tx_hash == "0xtxhash"
        assert proof.log_index == 0
        assert proof.address == "0xe034d479edc2530d9917dda4547b59bf0964a2ca"
        assert len(proof.topics) == 1
        assert proof.verified is True

    @pytest.mark.asyncio
    async def test_verify_event_second_log(self, client):
        async def mock_rpc(method, params):
            return SAMPLE_TX_RECEIPT["result"]

        client._execution_rpc = mock_rpc

        proof = await client.verify_event("0xtxhash", 1)
        assert proof.log_index == 1
        assert proof.topics == ["0xabcdef"]

    @pytest.mark.asyncio
    async def test_verify_event_no_receipt(self, client):
        async def mock_rpc(method, params):
            return None

        client._execution_rpc = mock_rpc

        with pytest.raises(KeyError, match="No receipt"):
            await client.verify_event("0xbadtx", 0)

    @pytest.mark.asyncio
    async def test_verify_event_bad_log_index(self, client):
        async def mock_rpc(method, params):
            return SAMPLE_TX_RECEIPT["result"]

        client._execution_rpc = mock_rpc

        with pytest.raises(KeyError, match="No log at index 99"):
            await client.verify_event("0xtxhash", 99)


# ---------------------------------------------------------------------------
# get_sync_committee tests
# ---------------------------------------------------------------------------


class TestGetSyncCommittee:

    @pytest.mark.asyncio
    async def test_cached_committee(self, client):
        committee = SyncCommittee(
            period=42, pubkeys=["0xaa"], aggregate_pubkey="0xbb"
        )
        client._committee_cache[42] = committee

        result = await client.get_sync_committee(42)
        assert result.period == 42

    @pytest.mark.asyncio
    async def test_fetch_committee(self, client):
        async def mock_get(path, **kwargs):
            return SAMPLE_LC_UPDATES_RESP

        client._beacon_get = mock_get

        result = await client.get_sync_committee(1221)
        assert result.period == 1221
        assert len(result.pubkeys) == 512

    @pytest.mark.asyncio
    async def test_fetch_committee_failure(self, client):
        async def mock_get(path, **kwargs):
            raise BeaconAPIError("Not available")

        client._beacon_get = mock_get

        with pytest.raises(KeyError, match="No sync committee"):
            await client.get_sync_committee(9999)


# ---------------------------------------------------------------------------
# get_latest_slot tests
# ---------------------------------------------------------------------------


class TestGetLatestSlot:

    @pytest.mark.asyncio
    async def test_synced_returns_cached(self, client):
        client._synced = True
        client._latest_slot = 12345
        client._finalized_header = BeaconHeader(
            slot=12345, proposer_index=0,
            parent_root="0x", state_root="0x", body_root="0x",
        )

        slot = await client.get_latest_slot()
        assert slot == 12345

    @pytest.mark.asyncio
    async def test_unsynced_fetches(self, client):
        async def mock_get(path, **kwargs):
            return SAMPLE_FINALIZED_HEADER_RESP

        client._beacon_get = mock_get
        slot = await client.get_latest_slot()
        assert slot == 10022528

    @pytest.mark.asyncio
    async def test_unsynced_api_failure(self, client):
        async def mock_get(path, **kwargs):
            raise BeaconAPIError("Failed")

        client._beacon_get = mock_get
        slot = await client.get_latest_slot()
        assert slot == 0  # Default


# ---------------------------------------------------------------------------
# Extended API tests
# ---------------------------------------------------------------------------


class TestExtendedAPI:

    @pytest.mark.asyncio
    async def test_get_execution_proof(self, client):
        async def mock_rpc(method, params):
            assert method == "eth_getProof"
            assert params[0] == "0xaddr"
            assert params[1] == ["0xslot1"]
            assert params[2] == "latest"
            return SAMPLE_ETH_GET_PROOF["result"]

        client._execution_rpc = mock_rpc

        result = await client.get_execution_proof("0xaddr", ["0xslot1"])
        assert "accountProof" in result

    @pytest.mark.asyncio
    async def test_get_execution_proof_null(self, client):
        async def mock_rpc(method, params):
            return None

        client._execution_rpc = mock_rpc

        with pytest.raises(ExecutionRPCError, match="null"):
            await client.get_execution_proof("0xaddr")

    @pytest.mark.asyncio
    async def test_get_finality_update(self, client):
        async def mock_get(path, **kwargs):
            return {"data": {"finalized_header": {"slot": 100}}}

        client._beacon_get = mock_get
        result = await client.get_finality_update()
        assert "data" in result

    @pytest.mark.asyncio
    async def test_get_chain_config(self, client):
        async def mock_get(path, **kwargs):
            return {"data": {"SLOTS_PER_EPOCH": "32"}}

        client._beacon_get = mock_get
        config = await client.get_chain_config()
        assert config["SLOTS_PER_EPOCH"] == "32"

    @pytest.mark.asyncio
    async def test_get_state_root(self, client):
        async def mock_get(path, **kwargs):
            return {"data": {"root": "0xaabbcc"}}

        client._beacon_get = mock_get
        root = await client.get_state_root("finalized")
        assert root == "0xaabbcc"

    @pytest.mark.asyncio
    async def test_get_block(self, client):
        async def mock_get(path, **kwargs):
            return {"data": {"message": {"slot": "100"}}}

        client._beacon_get = mock_get
        block = await client.get_block("finalized")
        assert "data" in block


# ---------------------------------------------------------------------------
# Properties tests
# ---------------------------------------------------------------------------


class TestProperties:

    def test_finalized_header_none_initially(self, client):
        assert client.finalized_header is None

    def test_finalized_block_root_empty_initially(self, client):
        assert client.finalized_block_root == ""

    def test_checkpoint_empty_initially(self, client):
        assert client.checkpoint == ""

    @pytest.mark.asyncio
    async def test_properties_after_sync(self, client):
        call_idx = [0]

        async def mock_get(path, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return SAMPLE_FINALIZED_HEADER_RESP
            return SAMPLE_BOOTSTRAP_RESP

        client._beacon_get = mock_get
        await client.sync()

        assert client.finalized_header is not None
        assert client.finalized_header.slot == 10022528
        assert client.finalized_block_root != ""
        assert client.checkpoint != ""


# ---------------------------------------------------------------------------
# Error class tests
# ---------------------------------------------------------------------------


class TestErrors:

    def test_beacon_api_error(self):
        err = BeaconAPIError("test", status_code=503, url="http://x")
        assert str(err) == "test"
        assert err.status_code == 503
        assert err.url == "http://x"

    def test_execution_rpc_error(self):
        err = ExecutionRPCError("rpc fail", code=-32600)
        assert str(err) == "rpc fail"
        assert err.code == -32600


# =========================================================================
# NETWORK INTEGRATION TESTS (require real Sepolia endpoints)
# =========================================================================

# Run with:  pytest -m network tests/test_beacon_client.py -v

SEPOLIA_BEACON = "https://ethereum-sepolia-beacon-api.publicnode.com"
SEPOLIA_EXECUTION = "https://ethereum-sepolia-rpc.publicnode.com"
BRIDGE_CONTRACT = "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca"


@pytest.mark.network
class TestNetworkSync:
    """Tests that connect to real Sepolia beacon API."""

    @pytest.mark.asyncio
    async def test_sync_and_latest_header(self):
        """Sync with Sepolia and get the finalized header."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
            fallback_beacon_url=None,
        ) as client:
            await client.sync()
            assert client.is_synced
            assert client._latest_slot > 0

            header = await client.latest_header()
            assert header.slot > 0
            assert header.state_root.startswith("0x")
            assert header.body_root.startswith("0x")
            print(f"\n  Finalized slot: {header.slot}")
            print(f"  State root: {header.state_root}")
            print(f"  Block root: {client.finalized_block_root}")

    @pytest.mark.asyncio
    async def test_get_header_by_slot(self):
        """Fetch a specific header by slot."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
            fallback_beacon_url=None,
        ) as client:
            await client.sync()
            slot = client._latest_slot

            header = await client.get_verified_header(slot)
            assert header.slot == slot
            print(f"\n  Fetched header for slot {slot}")

    @pytest.mark.asyncio
    async def test_get_sync_committee(self):
        """Fetch the current sync committee."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
            fallback_beacon_url=None,
        ) as client:
            await client.sync()
            period = slot_to_sync_committee_period(client._latest_slot)
            committee = await client.get_sync_committee(period)
            assert committee.period == period
            assert len(committee.pubkeys) == 512
            assert committee.aggregate_pubkey.startswith("0x")
            print(f"\n  Sync committee period: {period}")
            print(f"  Pubkeys: {len(committee.pubkeys)}")

    @pytest.mark.asyncio
    async def test_eth_get_proof(self):
        """Fetch eth_getProof for the bridge contract."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
            fallback_beacon_url=None,
        ) as client:
            raw = await client.get_execution_proof(
                BRIDGE_CONTRACT, storage_keys=[], block="latest"
            )
            assert "accountProof" in raw
            assert "balance" in raw
            assert "nonce" in raw
            print(f"\n  Bridge contract proof:")
            print(f"    Balance: {int(raw['balance'], 16)} wei")
            print(f"    Nonce: {int(raw['nonce'], 16)}")
            print(f"    Code hash: {raw['codeHash']}")
            print(f"    Account proof nodes: {len(raw['accountProof'])}")

    @pytest.mark.asyncio
    async def test_verify_state_proof(self):
        """Fetch and verify state proof for the bridge contract."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
            fallback_beacon_url=None,
        ) as client:
            await client.sync()

            # Get latest block number from execution layer
            block_num_hex = await client._execution_rpc(
                "eth_blockNumber", []
            )
            block_num = int(block_num_hex, 16)

            proof = await client.verify_state_proof(
                BRIDGE_CONTRACT, [], block=block_num
            )
            assert proof.address == BRIDGE_CONTRACT
            assert proof.nonce >= 0
            assert proof.balance >= 0
            print(f"\n  State proof for {BRIDGE_CONTRACT}:")
            print(f"    Block: {proof.block_number}")
            print(f"    Balance: {proof.balance} wei")
            print(f"    Nonce: {proof.nonce}")
            print(f"    Verified: {proof.verified}")

    @pytest.mark.asyncio
    async def test_mpt_proof_verification(self):
        """Verify an MPT proof against a real state root."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
            fallback_beacon_url=None,
        ) as client:
            # Get the latest block with its state root
            block_num_hex = await client._execution_rpc(
                "eth_blockNumber", []
            )
            block_num = int(block_num_hex, 16)

            # Get the block to find the state root
            block = await client._execution_rpc(
                "eth_getBlockByNumber", [hex(block_num), False]
            )
            state_root_hex = block["stateRoot"]
            state_root = bytes.fromhex(state_root_hex[2:])

            # Get the proof
            raw = await client._execution_rpc(
                "eth_getProof", [BRIDGE_CONTRACT, [], hex(block_num)]
            )

            # Verify with MPT verifier
            proof_nodes = [
                bytes.fromhex(p[2:]) for p in raw["accountProof"]
            ]
            result = MerklePatriciaVerifier.verify_account_proof(
                state_root, BRIDGE_CONTRACT, proof_nodes
            )

            assert result is not None, (
                f"MPT verification failed for state root {state_root_hex}"
            )
            assert result.nonce >= 0
            assert result.balance >= 0
            print(f"\n  MPT verification SUCCESS:")
            print(f"    State root: {state_root_hex}")
            print(f"    Nonce: {result.nonce}")
            print(f"    Balance: {result.balance}")
            print(f"    Storage root: {result.storage_root.hex()}")
            print(f"    Code hash: {result.code_hash.hex()}")

    @pytest.mark.asyncio
    async def test_get_finality_update(self):
        """Fetch the latest finality update."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
            fallback_beacon_url=None,
        ) as client:
            update = await client.get_finality_update()
            assert "data" in update
            finalized = update["data"]["finalized_header"]["beacon"]
            assert int(finalized["slot"]) > 0
            print(f"\n  Finality update finalized slot: {finalized['slot']}")

    @pytest.mark.asyncio
    async def test_get_chain_config(self):
        """Fetch chain configuration."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
            fallback_beacon_url=None,
        ) as client:
            config = await client.get_chain_config()
            assert "SLOTS_PER_EPOCH" in config
            assert config["SLOTS_PER_EPOCH"] == "32"
            print(f"\n  Chain config SLOTS_PER_EPOCH: {config['SLOTS_PER_EPOCH']}")
            print(f"  SECONDS_PER_SLOT: {config['SECONDS_PER_SLOT']}")

    @pytest.mark.asyncio
    async def test_full_sync_flow(self):
        """Full flow: sync → header → committee → proof → verify."""
        async with BeaconAPILightClient(
            beacon_url=SEPOLIA_BEACON,
            execution_url=SEPOLIA_EXECUTION,
        ) as client:
            # Step 1: Sync
            await client.sync()
            assert client.is_synced
            print(f"\n  Step 1: Synced at slot {client._latest_slot}")

            # Step 2: Get finalized header
            header = await client.latest_header()
            assert header.slot > 0
            print(f"  Step 2: Finalized header at slot {header.slot}")

            # Step 3: Get sync committee
            period = slot_to_sync_committee_period(header.slot)
            committee = await client.get_sync_committee(period)
            assert len(committee.pubkeys) == 512
            print(f"  Step 3: Sync committee period {period}, {len(committee.pubkeys)} validators")

            # Step 4: Get execution proof
            raw = await client.get_execution_proof(
                BRIDGE_CONTRACT, block="latest"
            )
            balance = int(raw["balance"], 16)
            print(f"  Step 4: Bridge contract balance = {balance} wei ({balance / 1e18:.6f} ETH)")

            # Step 5: MPT verification
            block_num_hex = await client._execution_rpc("eth_blockNumber", [])
            block_num = int(block_num_hex, 16)
            block = await client._execution_rpc(
                "eth_getBlockByNumber", [hex(block_num), False]
            )
            state_root = bytes.fromhex(block["stateRoot"][2:])
            proof_nodes = [
                bytes.fromhex(p[2:]) for p in raw["accountProof"]
            ]
            account = MerklePatriciaVerifier.verify_account_proof(
                state_root, BRIDGE_CONTRACT, proof_nodes
            )
            assert account is not None
            print(f"  Step 5: MPT verified — nonce={account.nonce}, balance={account.balance}")
            print(f"  ✓ Full sync flow complete!")
