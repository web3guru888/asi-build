"""
Tests for Rings-Side Token Ledger
==================================

Comprehensive tests for :mod:`asi_build.rings.bridge.ledger`:

- Balance queries (empty, after credit, after transfer)
- Transfer happy path (propose → attest → finalize → balances updated)
- Double-spend prevention (two concurrent transfers exceed balance)
- Insufficient balance rejection
- Threshold behavior (3/6 not enough, 4/6 finalizes)
- Bridge credit (deposit → balance appears)
- Bridge debit (withdrawal lock → balance decremented)
- Transfer history / lookup
- Signature verification (reject forged signatures)
- Concurrent transfers from same DID (locking)
- Edge cases: zero amounts, self-transfers, unknown tokens
- Nonce management
- Expiry of stale transfers
- Withdrawal lock lifecycle
- Token normalization
- DHT key schema
- Statistics tracking
- Bulk credit operations
- Error handling and edge cases
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asi_build.rings.bridge.ledger import (
    DEFAULT_THRESHOLD,
    DEFAULT_TOTAL,
    DEFAULT_TRANSFER_TTL,
    ETH_TOKEN,
    ETH_ZERO_ADDRESS,
    LEDGER_NS,
    MAX_HISTORY_PER_DID,
    LedgerKeys,
    LedgerMessage,
    RingsTokenLedger,
    TransferRecord,
    TransferReceipt,
    TransferStatus,
    WithdrawalLock,
    _compute_attestation_digest,
    _compute_transfer_digest,
    _normalize_token,
)
from asi_build.rings.client import InMemoryTransport, RingsClient


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


class MockIdentity:
    """Mock identity with sign_rings / rings_did for testing."""

    def __init__(self, did: str = "did:rings:secp256k1:validator1", seed: int = 42):
        self.rings_did = did
        self._seed = seed

    def sign_rings(self, data: bytes) -> bytes:
        """Deterministic mock signature: HMAC-like sha256(seed || data)."""
        return hashlib.sha256(self._seed.to_bytes(8, "big") + data).digest()


def make_identities(n: int = 6) -> List[MockIdentity]:
    """Create n distinct mock identities."""
    return [
        MockIdentity(did=f"did:rings:secp256k1:validator{i}", seed=100 + i)
        for i in range(n)
    ]


@pytest.fixture
def transport():
    """Fresh InMemoryTransport."""
    return InMemoryTransport()


@pytest.fixture
def client(transport):
    """Connected RingsClient with in-memory transport."""
    c = RingsClient(transport=transport)
    # Manually set connected state for testing
    c._state = c._state.__class__("connected")
    c._transport._connected = True
    return c


@pytest.fixture
def identity():
    """Default mock identity."""
    return MockIdentity()


@pytest.fixture
def ledger(client, identity):
    """Fresh RingsTokenLedger with default config."""
    return RingsTokenLedger(client, identity)


@pytest.fixture
def ledger_no_identity(client):
    """Ledger with no identity (cannot attest)."""
    return RingsTokenLedger(client)


DID_ALICE = "did:rings:secp256k1:alice"
DID_BOB = "did:rings:secp256k1:bob"
DID_CAROL = "did:rings:secp256k1:carol"
TOKEN_USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
TOKEN_USDC_MIXED = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
MOCK_SIG = b"\x01" * 32


# ---------------------------------------------------------------------------
# Token Normalization
# ---------------------------------------------------------------------------


class TestTokenNormalization:
    """Tests for _normalize_token()."""

    def test_eth_string(self):
        assert _normalize_token("ETH") == "ETH"

    def test_eth_lowercase(self):
        assert _normalize_token("eth") == "ETH"

    def test_eth_zero_address(self):
        assert _normalize_token(ETH_ZERO_ADDRESS) == "ETH"

    def test_erc20_lowercased(self):
        result = _normalize_token(TOKEN_USDC_MIXED)
        assert result == TOKEN_USDC

    def test_arbitrary_token(self):
        assert _normalize_token("MYTOKEN") == "MYTOKEN"

    def test_short_hex(self):
        assert _normalize_token("0xabc") == "0xabc"


# ---------------------------------------------------------------------------
# DHT Key Schema
# ---------------------------------------------------------------------------


class TestLedgerKeys:
    """Tests for LedgerKeys static methods."""

    def test_balance_key(self):
        k = LedgerKeys.balance_key(DID_ALICE, "ETH")
        assert k == f"{LEDGER_NS}:balance:{DID_ALICE}:ETH"

    def test_transfer_key(self):
        k = LedgerKeys.transfer_key("tx-123")
        assert k == f"{LEDGER_NS}:tx:tx-123"

    def test_history_key(self):
        k = LedgerKeys.history_key(DID_BOB)
        assert k == f"{LEDGER_NS}:history:{DID_BOB}"

    def test_lock_key(self):
        k = LedgerKeys.lock_key(DID_ALICE, TOKEN_USDC_MIXED)
        assert k == f"{LEDGER_NS}:lock:{DID_ALICE}:{TOKEN_USDC}"

    def test_nonce_key(self):
        k = LedgerKeys.nonce_key(DID_ALICE)
        assert k == f"{LEDGER_NS}:nonce:{DID_ALICE}"

    def test_withdrawal_lock_key(self):
        k = LedgerKeys.withdrawal_lock_key("lock-456")
        assert k == f"{LEDGER_NS}:wdlock:lock-456"


# ---------------------------------------------------------------------------
# Digest Helpers
# ---------------------------------------------------------------------------


class TestDigestHelpers:
    """Tests for _compute_transfer_digest and _compute_attestation_digest."""

    def test_transfer_digest_deterministic(self):
        d1 = _compute_transfer_digest(DID_ALICE, DID_BOB, "ETH", 100, 0)
        d2 = _compute_transfer_digest(DID_ALICE, DID_BOB, "ETH", 100, 0)
        assert d1 == d2
        assert len(d1) == 32

    def test_transfer_digest_varies(self):
        d1 = _compute_transfer_digest(DID_ALICE, DID_BOB, "ETH", 100, 0)
        d2 = _compute_transfer_digest(DID_ALICE, DID_BOB, "ETH", 200, 0)
        assert d1 != d2

    def test_attestation_digest_deterministic(self):
        d1 = _compute_attestation_digest("tx-1", DID_ALICE, 100)
        d2 = _compute_attestation_digest("tx-1", DID_ALICE, 100)
        assert d1 == d2
        assert len(d1) == 32

    def test_attestation_digest_varies_on_amount(self):
        d1 = _compute_attestation_digest("tx-1", DID_ALICE, 100)
        d2 = _compute_attestation_digest("tx-1", DID_ALICE, 200)
        assert d1 != d2


# ---------------------------------------------------------------------------
# Data Records
# ---------------------------------------------------------------------------


class TestTransferRecord:
    """Tests for TransferRecord serialization."""

    def test_roundtrip(self):
        rec = TransferRecord(
            transfer_id="tx-abc",
            from_did=DID_ALICE,
            to_did=DID_BOB,
            token="ETH",
            amount=1000,
            nonce=1,
            signature="aabbcc",
            status=TransferStatus.ATTESTING,
            attestations={"v1": "deadbeef"},
        )
        d = rec.to_dict()
        rec2 = TransferRecord.from_dict(d)
        assert rec2.transfer_id == "tx-abc"
        assert rec2.from_did == DID_ALICE
        assert rec2.to_did == DID_BOB
        assert rec2.token == "ETH"
        assert rec2.amount == 1000
        assert rec2.status == TransferStatus.ATTESTING
        assert rec2.attestations == {"v1": "deadbeef"}

    def test_default_values(self):
        rec = TransferRecord(
            transfer_id="tx-1",
            from_did=DID_ALICE,
            to_did=DID_BOB,
            token="ETH",
            amount=100,
        )
        assert rec.nonce == 0
        assert rec.status == TransferStatus.PROPOSED
        assert rec.attestations == {}
        assert rec.error == ""


class TestTransferReceipt:
    """Tests for TransferReceipt."""

    def test_to_dict(self):
        r = TransferReceipt(
            transfer_id="tx-1",
            status=TransferStatus.PROPOSED,
            attestation_count=2,
        )
        d = r.to_dict()
        assert d["transfer_id"] == "tx-1"
        assert d["status"] == "proposed"
        assert d["attestation_count"] == 2


class TestWithdrawalLock:
    """Tests for WithdrawalLock serialization."""

    def test_roundtrip(self):
        lock = WithdrawalLock(
            lock_id="lock-1",
            did=DID_ALICE,
            token="ETH",
            amount=500,
        )
        d = lock.to_dict()
        lock2 = WithdrawalLock.from_dict(d)
        assert lock2.lock_id == "lock-1"
        assert lock2.did == DID_ALICE
        assert lock2.amount == 500
        assert lock2.released is False


# ---------------------------------------------------------------------------
# Constructor & Validation
# ---------------------------------------------------------------------------


class TestLedgerConstruction:
    """Tests for RingsTokenLedger construction."""

    def test_default_threshold(self, client, identity):
        led = RingsTokenLedger(client, identity)
        assert led.threshold == DEFAULT_THRESHOLD
        assert led.total == DEFAULT_TOTAL

    def test_custom_threshold(self, client, identity):
        led = RingsTokenLedger(client, identity, threshold=3, total=5)
        assert led.threshold == 3
        assert led.total == 5

    def test_threshold_exceeds_total_raises(self, client, identity):
        with pytest.raises(ValueError, match="cannot exceed"):
            RingsTokenLedger(client, identity, threshold=7, total=6)

    def test_zero_threshold_raises(self, client, identity):
        with pytest.raises(ValueError, match="must be ≥ 1"):
            RingsTokenLedger(client, identity, threshold=0)

    def test_no_identity(self, client):
        led = RingsTokenLedger(client)
        assert led.validator_did is None

    def test_validator_did(self, ledger):
        assert ledger.validator_did == "did:rings:secp256k1:validator1"

    def test_repr(self, ledger):
        r = repr(ledger)
        assert "RingsTokenLedger" in r
        assert "threshold" in r


# ---------------------------------------------------------------------------
# Balance Queries
# ---------------------------------------------------------------------------


class TestBalanceQueries:
    """Tests for balance(), balances(), available_balance()."""

    @pytest.mark.asyncio
    async def test_empty_balance(self, ledger):
        b = await ledger.balance(DID_ALICE, "ETH")
        assert b == 0

    @pytest.mark.asyncio
    async def test_balance_after_credit(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        b = await ledger.balance(DID_ALICE, "ETH")
        assert b == 1000

    @pytest.mark.asyncio
    async def test_balances_all_tokens(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 500)
        await ledger.credit_from_bridge(DID_ALICE, TOKEN_USDC, 2000)
        all_b = await ledger.balances(DID_ALICE)
        assert all_b["ETH"] == 500
        assert all_b[TOKEN_USDC] == 2000

    @pytest.mark.asyncio
    async def test_balances_empty(self, ledger):
        all_b = await ledger.balances(DID_ALICE)
        assert all_b == {}

    @pytest.mark.asyncio
    async def test_available_balance_no_locks(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        avail = await ledger.available_balance(DID_ALICE, "ETH")
        assert avail == 1000

    @pytest.mark.asyncio
    async def test_balance_from_dht(self, ledger, client):
        """Balance fetched from DHT when not in local cache."""
        key = LedgerKeys.balance_key(DID_ALICE, "ETH")
        await client.dht_put(key, 999)
        # Clear local cache
        ledger._balances = {}
        b = await ledger.balance(DID_ALICE, "ETH")
        assert b == 999

    @pytest.mark.asyncio
    async def test_balance_string_from_dht(self, ledger, client):
        """Balance stored as string in DHT is parsed correctly."""
        key = LedgerKeys.balance_key(DID_ALICE, "ETH")
        await client.dht_put(key, "12345")
        ledger._balances = {}
        b = await ledger.balance(DID_ALICE, "ETH")
        assert b == 12345


# ---------------------------------------------------------------------------
# Bridge Credit
# ---------------------------------------------------------------------------


class TestBridgeCredit:
    """Tests for credit_from_bridge()."""

    @pytest.mark.asyncio
    async def test_basic_credit(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        assert await ledger.balance(DID_ALICE, "ETH") == 1000

    @pytest.mark.asyncio
    async def test_cumulative_credit(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 500)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 300)
        assert await ledger.balance(DID_ALICE, "ETH") == 800

    @pytest.mark.asyncio
    async def test_credit_different_tokens(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 100)
        await ledger.credit_from_bridge(DID_ALICE, TOKEN_USDC, 500)
        assert await ledger.balance(DID_ALICE, "ETH") == 100
        assert await ledger.balance(DID_ALICE, TOKEN_USDC) == 500

    @pytest.mark.asyncio
    async def test_credit_zero_raises(self, ledger):
        with pytest.raises(ValueError, match="must be > 0"):
            await ledger.credit_from_bridge(DID_ALICE, "ETH", 0)

    @pytest.mark.asyncio
    async def test_credit_negative_raises(self, ledger):
        with pytest.raises(ValueError, match="must be > 0"):
            await ledger.credit_from_bridge(DID_ALICE, "ETH", -10)

    @pytest.mark.asyncio
    async def test_credit_empty_did_raises(self, ledger):
        with pytest.raises(ValueError, match="non-empty"):
            await ledger.credit_from_bridge("", "ETH", 100)

    @pytest.mark.asyncio
    async def test_credit_with_deposit_proof(self, ledger):
        proof = MagicMock()
        proof.tx_hash = "0xabc"
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 100, deposit_proof=proof)
        assert await ledger.balance(DID_ALICE, "ETH") == 100

    @pytest.mark.asyncio
    async def test_credit_normalizes_token(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, TOKEN_USDC_MIXED, 100)
        assert await ledger.balance(DID_ALICE, TOKEN_USDC) == 100

    @pytest.mark.asyncio
    async def test_credit_stats(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 100)
        assert ledger.stats["credits"] == 1

    @pytest.mark.asyncio
    async def test_credit_persists_to_dht(self, ledger, client):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 500)
        key = LedgerKeys.balance_key(DID_ALICE, "ETH")
        raw = await client.dht_get(key)
        assert raw == 500


# ---------------------------------------------------------------------------
# Bridge Debit (Withdrawal Lock)
# ---------------------------------------------------------------------------


class TestBridgeDebit:
    """Tests for debit_for_withdrawal() and lock lifecycle."""

    @pytest.mark.asyncio
    async def test_basic_debit(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        lock = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 500)
        assert lock.amount == 500
        assert lock.did == DID_ALICE
        assert lock.token == "ETH"
        assert not lock.released

    @pytest.mark.asyncio
    async def test_debit_reduces_available(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 600)
        avail = await ledger.available_balance(DID_ALICE, "ETH")
        assert avail == 400

    @pytest.mark.asyncio
    async def test_debit_insufficient_raises(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 100)
        with pytest.raises(ValueError, match="insufficient"):
            await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 200)

    @pytest.mark.asyncio
    async def test_debit_zero_raises(self, ledger):
        with pytest.raises(ValueError, match="must be > 0"):
            await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 0)

    @pytest.mark.asyncio
    async def test_debit_empty_did_raises(self, ledger):
        with pytest.raises(ValueError, match="non-empty"):
            await ledger.debit_for_withdrawal("", "ETH", 100)

    @pytest.mark.asyncio
    async def test_release_lock(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        lock = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 600)

        # Release: funds deducted from total balance
        await ledger.release_withdrawal_lock(lock.lock_id)
        assert await ledger.balance(DID_ALICE, "ETH") == 400
        avail = await ledger.available_balance(DID_ALICE, "ETH")
        assert avail == 400

    @pytest.mark.asyncio
    async def test_cancel_lock(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        lock = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 600)

        # Cancel: funds returned to available
        await ledger.cancel_withdrawal_lock(lock.lock_id)
        assert await ledger.balance(DID_ALICE, "ETH") == 1000
        avail = await ledger.available_balance(DID_ALICE, "ETH")
        assert avail == 1000

    @pytest.mark.asyncio
    async def test_double_release_raises(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        lock = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 500)
        await ledger.release_withdrawal_lock(lock.lock_id)
        with pytest.raises(ValueError, match="already released"):
            await ledger.release_withdrawal_lock(lock.lock_id)

    @pytest.mark.asyncio
    async def test_double_cancel_raises(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        lock = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 500)
        await ledger.cancel_withdrawal_lock(lock.lock_id)
        with pytest.raises(ValueError, match="already released"):
            await ledger.cancel_withdrawal_lock(lock.lock_id)

    @pytest.mark.asyncio
    async def test_unknown_lock_raises(self, ledger):
        with pytest.raises(KeyError, match="Unknown withdrawal lock"):
            await ledger.release_withdrawal_lock("nonexistent")

    @pytest.mark.asyncio
    async def test_debit_stats(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 200)
        assert ledger.stats["debits"] == 1

    @pytest.mark.asyncio
    async def test_multiple_debits(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        lock1 = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 300)
        lock2 = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 400)
        avail = await ledger.available_balance(DID_ALICE, "ETH")
        assert avail == 300

    @pytest.mark.asyncio
    async def test_debit_then_credit_then_debit(self, ledger):
        """Debit, credit more, debit again — balances stay consistent."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 500)
        lock1 = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 300)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 200)
        # Balance: 700 total, 300 locked → 400 available
        avail = await ledger.available_balance(DID_ALICE, "ETH")
        assert avail == 400

    @pytest.mark.asyncio
    async def test_lock_from_dht(self, ledger, client):
        """Release a lock that only exists in DHT (not local cache)."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        lock = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 500)

        # Clear local cache to force DHT lookup
        lock_id = lock.lock_id
        del ledger._withdrawal_locks[lock_id]

        await ledger.release_withdrawal_lock(lock_id)
        assert await ledger.balance(DID_ALICE, "ETH") == 500


# ---------------------------------------------------------------------------
# Transfer Happy Path
# ---------------------------------------------------------------------------


class TestTransferHappyPath:
    """Tests for the full transfer lifecycle: propose → attest → finalize."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, client, identity):
        """Complete transfer with 4 validator attestations."""
        identities = make_identities(6)
        ledger = RingsTokenLedger(client, identities[0], threshold=4, total=6)

        # Credit sender
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        # Propose transfer
        receipt = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 300, MOCK_SIG)
        assert receipt.status == TransferStatus.PROPOSED
        assert receipt.transfer_id != ""
        tid = receipt.transfer_id

        # 4 validators attest (using separate ledger instances)
        for i in range(4):
            led_i = RingsTokenLedger(client, identities[i], threshold=4, total=6)
            sig = await led_i.attest_transfer(tid)
            assert sig is not None

        # Collect attestations — should finalize
        met, sigs = await ledger.collect_transfer_attestations(tid)
        assert met is True
        assert len(sigs) >= 4

        # Check balances
        assert await ledger.balance(DID_ALICE, "ETH") == 700
        assert await ledger.balance(DID_BOB, "ETH") == 300

    @pytest.mark.asyncio
    async def test_transfer_receipt_fields(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        receipt = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        assert receipt.status == TransferStatus.PROPOSED
        assert receipt.attestation_count == 0
        assert receipt.threshold == DEFAULT_THRESHOLD
        assert receipt.error == ""

    @pytest.mark.asyncio
    async def test_transfer_creates_history(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        receipt = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)

        # Both sender and recipient should have history
        alice_hist = await ledger.transfer_history(DID_ALICE)
        bob_hist = await ledger.transfer_history(DID_BOB)
        assert len(alice_hist) == 1
        assert len(bob_hist) == 1
        assert alice_hist[0].transfer_id == receipt.transfer_id


# ---------------------------------------------------------------------------
# Threshold Behavior
# ---------------------------------------------------------------------------


class TestThresholdBehavior:
    """Tests for attestation threshold (4/6 default)."""

    @pytest.mark.asyncio
    async def test_below_threshold_not_finalized(self, client):
        identities = make_identities(6)
        ledger = RingsTokenLedger(client, identities[0], threshold=4, total=6)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        receipt = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 300, MOCK_SIG)
        tid = receipt.transfer_id

        # Only 3 attestations (below threshold)
        for i in range(3):
            led_i = RingsTokenLedger(client, identities[i], threshold=4, total=6)
            await led_i.attest_transfer(tid)

        met, sigs = await ledger.collect_transfer_attestations(tid)
        assert met is False
        assert len(sigs) == 3

        # Balances should NOT have changed
        # (sender's balance is still 1000 but 300 is locked)
        assert await ledger.balance(DID_ALICE, "ETH") == 1000

    @pytest.mark.asyncio
    async def test_exact_threshold_finalizes(self, client):
        identities = make_identities(6)
        ledger = RingsTokenLedger(client, identities[0], threshold=4, total=6)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        receipt = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 300, MOCK_SIG)
        tid = receipt.transfer_id

        # Exactly 4 attestations
        for i in range(4):
            led_i = RingsTokenLedger(client, identities[i], threshold=4, total=6)
            await led_i.attest_transfer(tid)

        met, sigs = await ledger.collect_transfer_attestations(tid)
        assert met is True
        assert len(sigs) == 4

    @pytest.mark.asyncio
    async def test_above_threshold_still_works(self, client):
        identities = make_identities(6)
        ledger = RingsTokenLedger(client, identities[0], threshold=4, total=6)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        receipt = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 300, MOCK_SIG)
        tid = receipt.transfer_id

        # All 6 attest
        for i in range(6):
            led_i = RingsTokenLedger(client, identities[i], threshold=4, total=6)
            await led_i.attest_transfer(tid)

        met, sigs = await ledger.collect_transfer_attestations(tid)
        assert met is True
        assert len(sigs) == 6

    @pytest.mark.asyncio
    async def test_threshold_1_of_1(self, client):
        """Minimal threshold — 1 attestation enough."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        receipt = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        tid = receipt.transfer_id
        await ledger.attest_transfer(tid)

        met, sigs = await ledger.collect_transfer_attestations(tid)
        assert met is True
        assert await ledger.balance(DID_ALICE, "ETH") == 900
        assert await ledger.balance(DID_BOB, "ETH") == 100


# ---------------------------------------------------------------------------
# Double-Spend Prevention
# ---------------------------------------------------------------------------


class TestDoubleSpendPrevention:
    """Tests for double-spend prevention via locking."""

    @pytest.mark.asyncio
    async def test_second_transfer_exceeds_available(self, ledger):
        """Two transfers that exceed total balance — second fails."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        # First transfer: 600 ETH (locks 600)
        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 600, MOCK_SIG)
        assert r1.status == TransferStatus.PROPOSED

        # Second transfer: 500 ETH — available is now 400 → FAIL
        r2 = await ledger.transfer(DID_ALICE, DID_CAROL, "ETH", 500, MOCK_SIG)
        assert r2.status == TransferStatus.FAILED
        assert "insufficient balance" in r2.error

    @pytest.mark.asyncio
    async def test_concurrent_exact_balance(self, ledger):
        """Two transfers that exactly use up balance — second fails."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1000, MOCK_SIG)
        assert r1.status == TransferStatus.PROPOSED

        r2 = await ledger.transfer(DID_ALICE, DID_CAROL, "ETH", 1, MOCK_SIG)
        assert r2.status == TransferStatus.FAILED

    @pytest.mark.asyncio
    async def test_after_finalization_can_use_received(self, client):
        """After transfer finalizes, recipient can use the funds."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)

        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        # Alice → Bob: 500
        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 500, MOCK_SIG)
        await ledger.attest_transfer(r1.transfer_id)
        await ledger.collect_transfer_attestations(r1.transfer_id)

        # Bob now has 500 and can send 200 to Carol
        r2 = await ledger.transfer(DID_BOB, DID_CAROL, "ETH", 200, MOCK_SIG)
        assert r2.status == TransferStatus.PROPOSED

    @pytest.mark.asyncio
    async def test_failed_transfer_releases_lock(self, ledger):
        """After fail_transfer(), the lock is released."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 800, MOCK_SIG)
        assert await ledger.available_balance(DID_ALICE, "ETH") == 200

        await ledger.fail_transfer(r1.transfer_id, "test failure")
        assert await ledger.available_balance(DID_ALICE, "ETH") == 1000


# ---------------------------------------------------------------------------
# Insufficient Balance Rejection
# ---------------------------------------------------------------------------


class TestInsufficientBalance:
    """Tests for balance validation on transfer."""

    @pytest.mark.asyncio
    async def test_no_balance(self, ledger):
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        assert r.status == TransferStatus.FAILED
        assert "insufficient" in r.error

    @pytest.mark.asyncio
    async def test_exact_balance(self, ledger):
        """Transferring exact balance should work."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 100)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        assert r.status == TransferStatus.PROPOSED

    @pytest.mark.asyncio
    async def test_one_over_balance(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 100)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 101, MOCK_SIG)
        assert r.status == TransferStatus.FAILED

    @pytest.mark.asyncio
    async def test_wrong_token(self, ledger):
        """Balance in ETH doesn't help for USDC transfer."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, TOKEN_USDC, 100, MOCK_SIG)
        assert r.status == TransferStatus.FAILED

    @pytest.mark.asyncio
    async def test_validator_rejects_insufficient(self, client):
        """Validator rejects attestation if sender doesn't have funds."""
        ids = make_identities(2)
        ledger1 = RingsTokenLedger(client, ids[0], threshold=1, total=1)
        ledger2 = RingsTokenLedger(client, ids[1], threshold=1, total=1)

        # Credit 100 to Alice, propose 200 transfer (bypass normal validation)
        await ledger1.credit_from_bridge(DID_ALICE, "ETH", 100)

        # Manually create a transfer record for 200 (more than balance)
        record = TransferRecord(
            transfer_id=str(uuid.uuid4()),
            from_did=DID_ALICE,
            to_did=DID_BOB,
            token="ETH",
            amount=200,
            signature=MOCK_SIG.hex(),
        )
        await ledger1._persist_transfer(record)

        # Validator 2 tries to attest — should reject
        sig = await ledger2.attest_transfer(record.transfer_id)
        assert sig is None


# ---------------------------------------------------------------------------
# Transfer Edge Cases
# ---------------------------------------------------------------------------


class TestTransferEdgeCases:
    """Edge cases for transfers."""

    @pytest.mark.asyncio
    async def test_zero_amount(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 0, MOCK_SIG)
        assert r.status == TransferStatus.FAILED
        assert "must be > 0" in r.error

    @pytest.mark.asyncio
    async def test_negative_amount(self, ledger):
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", -50, MOCK_SIG)
        assert r.status == TransferStatus.FAILED

    @pytest.mark.asyncio
    async def test_self_transfer(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_ALICE, "ETH", 100, MOCK_SIG)
        assert r.status == TransferStatus.FAILED
        assert "self" in r.error

    @pytest.mark.asyncio
    async def test_empty_from_did(self, ledger):
        r = await ledger.transfer("", DID_BOB, "ETH", 100, MOCK_SIG)
        assert r.status == TransferStatus.FAILED
        assert "non-empty" in r.error

    @pytest.mark.asyncio
    async def test_empty_to_did(self, ledger):
        r = await ledger.transfer(DID_ALICE, "", "ETH", 100, MOCK_SIG)
        assert r.status == TransferStatus.FAILED
        assert "non-empty" in r.error

    @pytest.mark.asyncio
    async def test_empty_token(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "", 100, MOCK_SIG)
        assert r.status == TransferStatus.FAILED
        assert "non-empty" in r.error

    @pytest.mark.asyncio
    async def test_unknown_transfer_id(self, ledger):
        rec = await ledger.get_transfer("nonexistent")
        assert rec is None

    @pytest.mark.asyncio
    async def test_fail_unknown_transfer(self, ledger):
        with pytest.raises(KeyError, match="Unknown transfer"):
            await ledger.fail_transfer("nonexistent")

    @pytest.mark.asyncio
    async def test_fail_already_finalized(self, client):
        """Failing an already-finalized transfer is a no-op."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        await ledger.attest_transfer(r.transfer_id)
        await ledger.collect_transfer_attestations(r.transfer_id)

        # This should be a no-op (already terminal)
        await ledger.fail_transfer(r.transfer_id, "too late")
        rec = await ledger.get_transfer(r.transfer_id)
        assert rec.status == TransferStatus.FINALIZED

    @pytest.mark.asyncio
    async def test_transfer_generates_unique_ids(self, ledger):
        """Each transfer gets a unique ID."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)
        ids = set()
        for _ in range(10):
            r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)
            ids.add(r.transfer_id)
        assert len(ids) == 10


# ---------------------------------------------------------------------------
# Attestation Edge Cases
# ---------------------------------------------------------------------------


class TestAttestationEdgeCases:
    """Tests for attestation behavior."""

    @pytest.mark.asyncio
    async def test_attest_no_identity(self, ledger_no_identity, client):
        """Ledger without identity cannot attest."""
        identity = MockIdentity()
        led2 = RingsTokenLedger(client, identity, threshold=1, total=1)
        await led2.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await led2.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)

        sig = await ledger_no_identity.attest_transfer(r.transfer_id)
        assert sig is None

    @pytest.mark.asyncio
    async def test_attest_unknown_transfer(self, ledger):
        sig = await ledger.attest_transfer("nonexistent-id")
        assert sig is None

    @pytest.mark.asyncio
    async def test_attest_finalized_transfer(self, client):
        """Cannot attest an already-finalized transfer."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        await ledger.attest_transfer(r.transfer_id)
        await ledger.collect_transfer_attestations(r.transfer_id)

        # Try to attest again — should refuse
        sig = await ledger.attest_transfer(r.transfer_id)
        assert sig is None

    @pytest.mark.asyncio
    async def test_duplicate_attestation(self, ledger):
        """Same validator attesting twice returns cached signature."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)

        sig1 = await ledger.attest_transfer(r.transfer_id)
        sig2 = await ledger.attest_transfer(r.transfer_id)
        assert sig1 == sig2

    @pytest.mark.asyncio
    async def test_attestation_stats(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        await ledger.attest_transfer(r.transfer_id)
        assert ledger.stats["attestations_given"] == 1

    @pytest.mark.asyncio
    async def test_collect_unknown_transfer(self, ledger):
        met, sigs = await ledger.collect_transfer_attestations("nonexistent")
        assert met is False
        assert sigs == []


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------


class TestExpiry:
    """Tests for transfer expiry."""

    @pytest.mark.asyncio
    async def test_expired_transfer_rejected(self, client):
        identity = MockIdentity()
        ledger = RingsTokenLedger(
            client, identity, threshold=1, total=1, transfer_ttl=0.01
        )
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)

        # Wait for expiry
        import time as _time
        _time.sleep(0.02)

        sig = await ledger.attest_transfer(r.transfer_id)
        assert sig is None

        rec = await ledger.get_transfer(r.transfer_id)
        assert rec.status == TransferStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_expire_stale_transfers(self, client):
        identity = MockIdentity()
        ledger = RingsTokenLedger(
            client, identity, threshold=4, total=6, transfer_ttl=0.01
        )
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)

        for _ in range(5):
            await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)

        import time as _time
        _time.sleep(0.02)

        count = await ledger.expire_stale_transfers()
        assert count == 5

        # Locks should be released
        avail = await ledger.available_balance(DID_ALICE, "ETH")
        assert avail == 10000

    @pytest.mark.asyncio
    async def test_expired_collect_returns_false(self, client):
        identity = MockIdentity()
        ledger = RingsTokenLedger(
            client, identity, threshold=4, total=6, transfer_ttl=0.01
        )
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)

        import time as _time
        _time.sleep(0.02)

        met, sigs = await ledger.collect_transfer_attestations(r.transfer_id)
        assert met is False

    @pytest.mark.asyncio
    async def test_non_expired_not_affected(self, client):
        identity = MockIdentity()
        ledger = RingsTokenLedger(
            client, identity, threshold=4, total=6, transfer_ttl=300
        )
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)
        await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)

        count = await ledger.expire_stale_transfers()
        assert count == 0


# ---------------------------------------------------------------------------
# Nonce Management
# ---------------------------------------------------------------------------


class TestNonceManagement:
    """Tests for nonce tracking."""

    @pytest.mark.asyncio
    async def test_initial_nonce(self, ledger):
        n = await ledger.get_nonce(DID_ALICE)
        assert n == 0

    @pytest.mark.asyncio
    async def test_nonce_increments(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)

        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)
        rec1 = await ledger.get_transfer(r1.transfer_id)
        assert rec1.nonce == 0

        r2 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)
        rec2 = await ledger.get_transfer(r2.transfer_id)
        assert rec2.nonce == 1

    @pytest.mark.asyncio
    async def test_nonce_per_did(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)
        await ledger.credit_from_bridge(DID_BOB, "ETH", 10000)

        await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)
        await ledger.transfer(DID_BOB, DID_ALICE, "ETH", 1, MOCK_SIG)

        assert await ledger.get_nonce(DID_ALICE) == 1
        assert await ledger.get_nonce(DID_BOB) == 1

    @pytest.mark.asyncio
    async def test_nonce_from_dht(self, ledger, client):
        """Nonce fetched from DHT when not in local cache."""
        key = LedgerKeys.nonce_key(DID_ALICE)
        await client.dht_put(key, 42)
        ledger._nonces = {}
        n = await ledger.get_nonce(DID_ALICE)
        assert n == 42


# ---------------------------------------------------------------------------
# Transfer History
# ---------------------------------------------------------------------------


class TestTransferHistory:
    """Tests for transfer_history()."""

    @pytest.mark.asyncio
    async def test_empty_history(self, ledger):
        hist = await ledger.transfer_history(DID_ALICE)
        assert hist == []

    @pytest.mark.asyncio
    async def test_history_order(self, ledger):
        """History returns newest first."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)

        ids = []
        for i in range(5):
            r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)
            ids.append(r.transfer_id)

        hist = await ledger.transfer_history(DID_ALICE, limit=5)
        assert len(hist) == 5
        # Newest first
        assert hist[0].transfer_id == ids[-1]

    @pytest.mark.asyncio
    async def test_history_limit(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)
        for _ in range(10):
            await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)

        hist = await ledger.transfer_history(DID_ALICE, limit=3)
        assert len(hist) == 3

    @pytest.mark.asyncio
    async def test_history_both_parties(self, ledger):
        """Both sender and recipient see the transfer in their history."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)

        alice_hist = await ledger.transfer_history(DID_ALICE)
        bob_hist = await ledger.transfer_history(DID_BOB)
        assert len(alice_hist) == 1
        assert len(bob_hist) == 1
        assert alice_hist[0].transfer_id == bob_hist[0].transfer_id


# ---------------------------------------------------------------------------
# Signature Verification
# ---------------------------------------------------------------------------


class TestSignatureVerification:
    """Tests for verify_transfer_signature() and verify_attestation_signature()."""

    def test_no_pubkey_returns_true(self, ledger):
        """Without a public key, verification is skipped (permissionless)."""
        rec = TransferRecord(
            transfer_id="tx-1",
            from_did=DID_ALICE,
            to_did=DID_BOB,
            token="ETH",
            amount=100,
            signature="deadbeef",
        )
        assert ledger.verify_transfer_signature(rec) is True

    def test_no_pubkey_attestation_returns_true(self, ledger):
        assert ledger.verify_attestation_signature(
            "tx-1", DID_ALICE, 100, "deadbeef"
        ) is True

    def test_invalid_signature_hex(self, ledger):
        """Invalid hex in signature should return False when pubkey given."""
        rec = TransferRecord(
            transfer_id="tx-1",
            from_did=DID_ALICE,
            to_did=DID_BOB,
            token="ETH",
            amount=100,
            signature="not-valid-hex!!!",
        )
        # Create a dummy pubkey object that would fail
        mock_key = MagicMock()
        assert ledger.verify_transfer_signature(rec, mock_key) is False

    def test_real_signature_verification(self):
        """Verify with real secp256k1 keys (from did.py)."""
        from asi_build.rings.did import DIDKeyPair, KeyCurve

        kp = DIDKeyPair.generate(curve=KeyCurve.SECP256K1, seed="test-sender")

        # Create a transfer and sign it properly
        digest = _compute_transfer_digest(DID_ALICE, DID_BOB, "ETH", 100, 0)
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        sig = kp._private_key_obj.sign(digest, ec.ECDSA(hashes.SHA256()))

        rec = TransferRecord(
            transfer_id="tx-1",
            from_did=DID_ALICE,
            to_did=DID_BOB,
            token="ETH",
            amount=100,
            nonce=0,
            signature=sig.hex(),
        )

        client = RingsClient(transport=InMemoryTransport())
        client._state = client._state.__class__("connected")
        client._transport._connected = True
        ledger = RingsTokenLedger(client)

        assert ledger.verify_transfer_signature(rec, kp._public_key_obj) is True

    def test_forged_signature_rejected(self):
        """Forged signature is rejected."""
        from asi_build.rings.did import DIDKeyPair, KeyCurve

        kp = DIDKeyPair.generate(curve=KeyCurve.SECP256K1, seed="test-sender")
        other = DIDKeyPair.generate(curve=KeyCurve.SECP256K1, seed="attacker")

        # Sign with OTHER key
        digest = _compute_transfer_digest(DID_ALICE, DID_BOB, "ETH", 100, 0)
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        sig = other._private_key_obj.sign(digest, ec.ECDSA(hashes.SHA256()))

        rec = TransferRecord(
            transfer_id="tx-1",
            from_did=DID_ALICE,
            to_did=DID_BOB,
            token="ETH",
            amount=100,
            nonce=0,
            signature=sig.hex(),
        )

        client = RingsClient(transport=InMemoryTransport())
        client._state = client._state.__class__("connected")
        client._transport._connected = True
        ledger = RingsTokenLedger(client)

        # Verify against sender's key — should fail
        assert ledger.verify_transfer_signature(rec, kp._public_key_obj) is False


# ---------------------------------------------------------------------------
# Concurrent Transfers from Same DID
# ---------------------------------------------------------------------------


class TestConcurrentTransfers:
    """Tests for concurrent transfers from the same sender."""

    @pytest.mark.asyncio
    async def test_sequential_within_balance(self, ledger):
        """Multiple transfers that fit within balance all succeed."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 200, MOCK_SIG)
        r2 = await ledger.transfer(DID_ALICE, DID_CAROL, "ETH", 300, MOCK_SIG)
        r3 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 400, MOCK_SIG)

        assert r1.status == TransferStatus.PROPOSED
        assert r2.status == TransferStatus.PROPOSED
        assert r3.status == TransferStatus.PROPOSED

        # 200 + 300 + 400 = 900 locked out of 1000
        avail = await ledger.available_balance(DID_ALICE, "ETH")
        assert avail == 100

    @pytest.mark.asyncio
    async def test_sequential_fourth_fails(self, ledger):
        """Fourth transfer exceeds remaining balance."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 400, MOCK_SIG)
        await ledger.transfer(DID_ALICE, DID_CAROL, "ETH", 400, MOCK_SIG)
        r3 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 300, MOCK_SIG)
        assert r3.status == TransferStatus.FAILED


# ---------------------------------------------------------------------------
# Bulk Credit
# ---------------------------------------------------------------------------


class TestBulkCredit:
    """Tests for credit_multiple()."""

    @pytest.mark.asyncio
    async def test_basic_bulk(self, ledger):
        credits = [
            (DID_ALICE, "ETH", 100),
            (DID_BOB, "ETH", 200),
            (DID_CAROL, TOKEN_USDC, 500),
        ]
        count = await ledger.credit_multiple(credits)
        assert count == 3
        assert await ledger.balance(DID_ALICE, "ETH") == 100
        assert await ledger.balance(DID_BOB, "ETH") == 200
        assert await ledger.balance(DID_CAROL, TOKEN_USDC) == 500

    @pytest.mark.asyncio
    async def test_bulk_with_failures(self, ledger):
        """Invalid credits are skipped, valid ones succeed."""
        credits = [
            (DID_ALICE, "ETH", 100),
            ("", "ETH", 50),  # will fail: empty DID
            (DID_BOB, "ETH", 200),
        ]
        count = await ledger.credit_multiple(credits)
        assert count == 2
        assert await ledger.balance(DID_ALICE, "ETH") == 100
        assert await ledger.balance(DID_BOB, "ETH") == 200


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestStatistics:
    """Tests for ledger.stats property."""

    @pytest.mark.asyncio
    async def test_initial_stats(self, ledger):
        s = ledger.stats
        assert s["transfers_proposed"] == 0
        assert s["transfers_finalized"] == 0
        assert s["transfers_failed"] == 0
        assert s["credits"] == 0
        assert s["debits"] == 0
        assert s["known_dids"] == 0
        assert s["threshold"] == DEFAULT_THRESHOLD
        assert s["total_validators"] == DEFAULT_TOTAL

    @pytest.mark.asyncio
    async def test_stats_after_operations(self, client):
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)

        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        await ledger.attest_transfer(r.transfer_id)
        await ledger.collect_transfer_attestations(r.transfer_id)

        s = ledger.stats
        assert s["credits"] == 1
        assert s["transfers_proposed"] == 1
        assert s["transfers_finalized"] == 1
        assert s["known_dids"] == 2  # Alice and Bob

    @pytest.mark.asyncio
    async def test_active_transfers_count(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)
        for _ in range(3):
            await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)

        s = ledger.stats
        assert s["active_transfers"] == 3

    @pytest.mark.asyncio
    async def test_active_withdrawal_locks(self, ledger):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        lock = await ledger.debit_for_withdrawal(DID_ALICE, "ETH", 200)
        assert ledger.stats["active_withdrawal_locks"] == 1

        await ledger.release_withdrawal_lock(lock.lock_id)
        assert ledger.stats["active_withdrawal_locks"] == 0


# ---------------------------------------------------------------------------
# Token-Specific Tests
# ---------------------------------------------------------------------------


class TestTokenSpecific:
    """Tests for various token scenarios."""

    @pytest.mark.asyncio
    async def test_eth_token_normalization(self, ledger):
        """ETH and zero-address both resolve to ETH."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 100)
        await ledger.credit_from_bridge(DID_ALICE, ETH_ZERO_ADDRESS, 200)
        assert await ledger.balance(DID_ALICE, "ETH") == 300

    @pytest.mark.asyncio
    async def test_mixed_case_erc20(self, ledger):
        """Mixed-case and lowercase ERC-20 addresses are the same."""
        await ledger.credit_from_bridge(DID_ALICE, TOKEN_USDC_MIXED, 100)
        assert await ledger.balance(DID_ALICE, TOKEN_USDC) == 100

    @pytest.mark.asyncio
    async def test_multiple_tokens_independent(self, ledger):
        """Balances of different tokens are independent."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        await ledger.credit_from_bridge(DID_ALICE, TOKEN_USDC, 5000)

        # Transfer ETH doesn't affect USDC
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 800, MOCK_SIG)
        assert r.status == TransferStatus.PROPOSED
        assert await ledger.available_balance(DID_ALICE, TOKEN_USDC) == 5000


# ---------------------------------------------------------------------------
# DHT Persistence
# ---------------------------------------------------------------------------


class TestDHTPersistence:
    """Tests for DHT read/write correctness."""

    @pytest.mark.asyncio
    async def test_transfer_persisted_to_dht(self, ledger, client):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)

        key = LedgerKeys.transfer_key(r.transfer_id)
        raw = await client.dht_get(key)
        assert raw is not None
        assert raw["from_did"] == DID_ALICE
        assert raw["amount"] == 100

    @pytest.mark.asyncio
    async def test_transfer_fetched_from_dht(self, ledger, client):
        """get_transfer() falls back to DHT when not in local cache."""
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        tid = r.transfer_id

        # Clear local cache
        del ledger._transfers[tid]

        rec = await ledger.get_transfer(tid)
        assert rec is not None
        assert rec.transfer_id == tid
        assert rec.amount == 100

    @pytest.mark.asyncio
    async def test_nonce_persisted(self, ledger, client):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 10000)
        await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 1, MOCK_SIG)

        key = LedgerKeys.nonce_key(DID_ALICE)
        raw = await client.dht_get(key)
        assert raw == 1

    @pytest.mark.asyncio
    async def test_lock_persisted(self, ledger, client):
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 300, MOCK_SIG)

        key = LedgerKeys.lock_key(DID_ALICE, "ETH")
        raw = await client.dht_get(key)
        assert raw == 300


# ---------------------------------------------------------------------------
# Propose Transfer (direct)
# ---------------------------------------------------------------------------


class TestProposeTransfer:
    """Tests for propose_transfer() direct call."""

    @pytest.mark.asyncio
    async def test_propose_sets_attesting(self, ledger):
        rec = TransferRecord(
            transfer_id="tx-direct",
            from_did=DID_ALICE,
            to_did=DID_BOB,
            token="ETH",
            amount=100,
        )
        tid = await ledger.propose_transfer(rec)
        assert tid == "tx-direct"

        stored = await ledger.get_transfer("tx-direct")
        assert stored.status == TransferStatus.ATTESTING


# ---------------------------------------------------------------------------
# E2E Multi-Transfer Scenarios
# ---------------------------------------------------------------------------


class TestE2EScenarios:
    """End-to-end scenarios with multiple operations."""

    @pytest.mark.asyncio
    async def test_deposit_transfer_withdraw(self, client):
        """Full cycle: deposit → transfer → withdraw."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)

        # 1. Alice deposits 1000 ETH via bridge
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        # 2. Alice transfers 300 to Bob
        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 300, MOCK_SIG)
        await ledger.attest_transfer(r.transfer_id)
        await ledger.collect_transfer_attestations(r.transfer_id)

        assert await ledger.balance(DID_ALICE, "ETH") == 700
        assert await ledger.balance(DID_BOB, "ETH") == 300

        # 3. Bob withdraws 200 back to Ethereum
        lock = await ledger.debit_for_withdrawal(DID_BOB, "ETH", 200)
        await ledger.release_withdrawal_lock(lock.lock_id)

        assert await ledger.balance(DID_BOB, "ETH") == 100

    @pytest.mark.asyncio
    async def test_chain_of_transfers(self, client):
        """Alice → Bob → Carol in sequence."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)

        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        # Alice → Bob: 500
        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 500, MOCK_SIG)
        await ledger.attest_transfer(r1.transfer_id)
        await ledger.collect_transfer_attestations(r1.transfer_id)

        # Bob → Carol: 200
        r2 = await ledger.transfer(DID_BOB, DID_CAROL, "ETH", 200, MOCK_SIG)
        await ledger.attest_transfer(r2.transfer_id)
        await ledger.collect_transfer_attestations(r2.transfer_id)

        assert await ledger.balance(DID_ALICE, "ETH") == 500
        assert await ledger.balance(DID_BOB, "ETH") == 300
        assert await ledger.balance(DID_CAROL, "ETH") == 200

    @pytest.mark.asyncio
    async def test_multi_token_transfers(self, client):
        """Transfers of different tokens independently."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)

        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        await ledger.credit_from_bridge(DID_ALICE, TOKEN_USDC, 5000)

        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 300, MOCK_SIG)
        r2 = await ledger.transfer(DID_ALICE, DID_BOB, TOKEN_USDC, 2000, MOCK_SIG)

        for r in (r1, r2):
            await ledger.attest_transfer(r.transfer_id)
            await ledger.collect_transfer_attestations(r.transfer_id)

        assert await ledger.balance(DID_ALICE, "ETH") == 700
        assert await ledger.balance(DID_BOB, "ETH") == 300
        assert await ledger.balance(DID_ALICE, TOKEN_USDC) == 3000
        assert await ledger.balance(DID_BOB, TOKEN_USDC) == 2000

    @pytest.mark.asyncio
    async def test_failed_and_retry(self, client):
        """Failed transfer released lock; retry succeeds."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)

        await ledger.credit_from_bridge(DID_ALICE, "ETH", 500)

        # Transfer all — proposed
        r1 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 500, MOCK_SIG)
        assert r1.status == TransferStatus.PROPOSED

        # Fail it
        await ledger.fail_transfer(r1.transfer_id, "timed out")

        # Retry — should succeed since lock was released
        r2 = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 500, MOCK_SIG)
        assert r2.status == TransferStatus.PROPOSED

    @pytest.mark.asyncio
    async def test_already_finalized_collect(self, client):
        """Calling collect on already-finalized returns True."""
        identity = MockIdentity()
        ledger = RingsTokenLedger(client, identity, threshold=1, total=1)
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)

        r = await ledger.transfer(DID_ALICE, DID_BOB, "ETH", 100, MOCK_SIG)
        await ledger.attest_transfer(r.transfer_id)
        met1, sigs1 = await ledger.collect_transfer_attestations(r.transfer_id)
        assert met1 is True

        # Call again — should still return True
        met2, sigs2 = await ledger.collect_transfer_attestations(r.transfer_id)
        assert met2 is True


# ---------------------------------------------------------------------------
# Broadcast (non-critical)
# ---------------------------------------------------------------------------


class TestBroadcast:
    """Tests for Sub-Ring broadcasting (non-blocking)."""

    @pytest.mark.asyncio
    async def test_broadcast_does_not_block_on_failure(self, client, identity):
        """Broadcast failure should not prevent the operation."""
        # Replace broadcast with a failing mock
        original = client.broadcast
        client.broadcast = AsyncMock(side_effect=Exception("network down"))

        ledger = RingsTokenLedger(client, identity)
        # credit_from_bridge should still succeed despite broadcast failure
        await ledger.credit_from_bridge(DID_ALICE, "ETH", 1000)
        assert await ledger.balance(DID_ALICE, "ETH") == 1000

        client.broadcast = original


# ---------------------------------------------------------------------------
# Ledger Message Enum
# ---------------------------------------------------------------------------


class TestLedgerMessage:
    def test_all_values(self):
        values = [m.value for m in LedgerMessage]
        assert "transfer_proposed" in values
        assert "transfer_finalized" in values
        assert "balance_credited" in values


class TestTransferStatus:
    def test_all_values(self):
        values = [s.value for s in TransferStatus]
        assert "proposed" in values
        assert "attesting" in values
        assert "finalized" in values
        assert "failed" in values
        assert "expired" in values
