"""
Tests for the bridge protocol definitions and BridgeValidator.
==============================================================

Covers:
- BridgeProtocol DHT key constructors
- BridgeMessage encode/decode
- DepositRecord / WithdrawalRecord data records
- BridgeValidator full lifecycle (async)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time

import pytest

from asi_build.rings.bridge.protocol import (
    BridgeMessage,
    BridgeProtocol,
    BridgeState,
    BridgeValidator,
    DepositRecord,
    WithdrawalRecord,
)
from asi_build.rings.client import InMemoryTransport, RingsClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockIdentity:
    """Duck-typed identity for BridgeValidator tests."""

    def __init__(self, seed: str = "test"):
        self._seed = seed
        h = hashlib.sha256(seed.encode()).hexdigest()
        self._did = f"did:rings:secp256k1:{h[:20]}"

    @property
    def rings_did(self) -> str:
        return self._did

    def sign_rings(self, data: bytes) -> bytes:
        return hmac.new(self._seed.encode(), data, hashlib.sha256).digest()


def run(coro):
    """Run an async coroutine synchronously (one-shot event loop)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _make_validator(
    seed: str = "v1",
    transport: InMemoryTransport | None = None,
    threshold: int = 2,
    total: int = 3,
) -> BridgeValidator:
    """Create a connected BridgeValidator with InMemoryTransport."""
    t = transport or InMemoryTransport()
    client = RingsClient(transport=t)
    await client.connect()
    identity = MockIdentity(seed)
    return BridgeValidator(identity, client, threshold=threshold, total=total)


# ===================================================================
# 1.  BridgeProtocol DHT Keys (8 tests)
# ===================================================================


class TestBridgeProtocolDHTKeys:
    """DHT key constructors produce deterministic, well-formatted strings."""

    def test_eth_header_key_format(self):
        assert BridgeProtocol.eth_header_key(123456) == "bridge:eth:header:123456"

    def test_eth_header_key_deterministic(self):
        assert BridgeProtocol.eth_header_key(42) == BridgeProtocol.eth_header_key(42)

    def test_eth_sync_committee_key_format(self):
        assert BridgeProtocol.eth_sync_committee_key(800) == "bridge:eth:committee:800"

    def test_eth_sync_committee_key_deterministic(self):
        k = BridgeProtocol.eth_sync_committee_key(1)
        assert k == BridgeProtocol.eth_sync_committee_key(1)

    def test_eth_state_proof_key_format(self):
        assert BridgeProtocol.eth_state_proof_key("0xabc", 100) == "bridge:eth:state:0xabc:100"

    def test_bridge_deposit_key_format(self):
        assert BridgeProtocol.bridge_deposit_key("0xdead") == "bridge:deposit:0xdead"

    def test_bridge_withdrawal_key_format(self):
        assert BridgeProtocol.bridge_withdrawal_key(7) == "bridge:withdrawal:7"

    def test_bridge_validator_key_format(self):
        did = "did:rings:ed25519:abc"
        assert BridgeProtocol.bridge_validator_key(did) == f"bridge:validator:{did}"

    def test_different_inputs_different_keys(self):
        assert BridgeProtocol.eth_header_key(1) != BridgeProtocol.eth_header_key(2)
        assert BridgeProtocol.bridge_deposit_key("a") != BridgeProtocol.bridge_deposit_key("b")

    def test_keys_are_strings(self):
        assert isinstance(BridgeProtocol.eth_header_key(0), str)
        assert isinstance(BridgeProtocol.bridge_validator_key("x"), str)


# ===================================================================
# 2.  BridgeMessage (4 tests)
# ===================================================================


class TestBridgeMessage:
    """Message encoding and decoding."""

    def test_encode_decode_roundtrip(self):
        payload = {"tx_hash": "0xaaa", "amount": 100}
        encoded = BridgeProtocol.encode_message(BridgeMessage.DEPOSIT_OBSERVED, payload)
        msg_type, decoded_payload = BridgeProtocol.decode_message(encoded)
        assert msg_type is BridgeMessage.DEPOSIT_OBSERVED
        assert decoded_payload == payload

    def test_decode_recovers_type_and_payload(self):
        raw = {"type": "heartbeat", "payload": {"v": 1}, "timestamp": 1.0}
        msg_type, payload = BridgeProtocol.decode_message(raw)
        assert msg_type is BridgeMessage.HEARTBEAT
        assert payload == {"v": 1}

    def test_invalid_message_type(self):
        raw = {"type": "bogus_type", "payload": {}}
        with pytest.raises(ValueError, match="Unknown bridge message type"):
            BridgeProtocol.decode_message(raw)

    def test_all_message_types_accessible(self):
        expected = {
            "deposit_observed", "deposit_attested",
            "withdrawal_request", "withdrawal_approved",
            "committee_update", "heartbeat", "emergency_halt",
        }
        actual = {m.value for m in BridgeMessage}
        assert actual == expected


# ===================================================================
# 3.  Data Records (5 tests)
# ===================================================================


class TestDataRecords:
    """DepositRecord and WithdrawalRecord creation and serialization."""

    def test_deposit_record_defaults(self):
        dr = DepositRecord(
            tx_hash="0x1", block_number=100, amount=1000,
            sender_eth="0xsender", recipient_did="did:r:1",
        )
        assert dr.finalized is False
        assert dr.attestations == {}
        assert isinstance(dr.timestamp, float)

    def test_withdrawal_record_defaults(self):
        wr = WithdrawalRecord(
            nonce=0, amount=500, requester_did="did:r:1",
            recipient_eth="0xrecipient",
        )
        assert wr.executed is False
        assert wr.approvals == {}

    def test_deposit_to_dict(self):
        dr = DepositRecord(
            tx_hash="0x1", block_number=10, amount=100,
            sender_eth="0xa", recipient_did="did:x",
            attestations={"did:v": b"\x01\x02"},
        )
        d = dr.to_dict()
        assert d["tx_hash"] == "0x1"
        assert d["attestations"]["did:v"] == "0102"

    def test_withdrawal_to_dict(self):
        wr = WithdrawalRecord(
            nonce=5, amount=200, requester_did="did:x",
            recipient_eth="0xb",
            approvals={"did:v": b"\xab\xcd"},
        )
        d = wr.to_dict()
        assert d["nonce"] == 5
        assert d["approvals"]["did:v"] == "abcd"

    def test_bridge_state_enum_values(self):
        assert BridgeState.INITIALIZING.value == "initializing"
        assert BridgeState.ACTIVE.value == "active"
        assert BridgeState.PAUSED.value == "paused"
        assert BridgeState.HALTED.value == "halted"


# ===================================================================
# 4.  BridgeValidator (18 tests)
# ===================================================================


class TestBridgeValidator:
    """Async tests for BridgeValidator lifecycle and operations."""

    def test_create_default_params(self):
        identity = MockIdentity("seed")
        transport = InMemoryTransport()
        client = RingsClient(transport=transport)
        v = BridgeValidator(identity, client, threshold=4, total=6)
        assert v.state == BridgeState.INITIALIZING
        assert v.threshold == 4
        assert v.total == 6
        assert v.did == identity.rings_did

    def test_join_bridge_sets_active(self):
        async def _test():
            v = await _make_validator()
            assert v.state == BridgeState.INITIALIZING
            await v.join_bridge()
            assert v.state == BridgeState.ACTIVE
        run(_test())

    def test_observe_deposit_stores_locally_and_dht(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            rec = await v.observe_deposit("0xaaa", 10, 1000, "0xsender", "did:r:1")
            assert rec.tx_hash == "0xaaa"
            assert "0xaaa" in v.deposits
            # Check DHT
            raw = await v.client.dht_get(BridgeProtocol.bridge_deposit_key("0xaaa"))
            assert raw is not None
            assert raw["amount"] == 1000
        run(_test())

    def test_observe_deposit_record_fields(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            rec = await v.observe_deposit("0xb", 5, 2000, "0xsender2", "did:r:2")
            assert rec.block_number == 5
            assert rec.amount == 2000
            assert rec.sender_eth == "0xsender2"
            assert rec.recipient_did == "did:r:2"
            assert rec.finalized is False
        run(_test())

    def test_attest_deposit_signs(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            await v.observe_deposit("0xc", 1, 100, "0xs", "did:r:1")
            sig = await v.attest_deposit("0xc")
            assert isinstance(sig, bytes)
            assert len(sig) == 32  # HMAC-SHA256
            assert v.did in v.deposits["0xc"].attestations
        run(_test())

    def test_attest_deposit_unknown_raises(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            with pytest.raises(KeyError, match="Unknown deposit"):
                await v.attest_deposit("0xnonexistent")
        run(_test())

    def test_collect_attestations_below_threshold(self):
        async def _test():
            v = await _make_validator(threshold=3, total=5)
            await v.join_bridge()
            await v.observe_deposit("0xd", 1, 100, "0xs", "did:r")
            await v.attest_deposit("0xd")
            met, sigs = await v.collect_attestations("0xd")
            assert met is False
            assert len(sigs) == 1
        run(_test())

    def test_collect_attestations_above_threshold(self):
        async def _test():
            transport = InMemoryTransport()
            # Create 2 validators sharing one transport (threshold=2)
            v1 = await _make_validator("v1", transport, threshold=2, total=2)
            v2 = await _make_validator("v2", transport, threshold=2, total=2)
            await v1.join_bridge()
            await v2.join_bridge()

            await v1.observe_deposit("0xe", 1, 100, "0xs", "did:r")
            await v1.attest_deposit("0xe")
            await v2.attest_deposit("0xe")  # v2 reads from DHT

            met, sigs = await v1.collect_attestations("0xe")
            assert met is True
            assert len(sigs) >= 2
        run(_test())

    def test_request_withdrawal_creates_record(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            rec = await v.request_withdrawal(500, "0xeth")
            assert rec.nonce == 0
            assert rec.amount == 500
            assert rec.recipient_eth == "0xeth"
            assert rec.requester_did == v.did
        run(_test())

    def test_request_withdrawal_increments_nonce(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            r1 = await v.request_withdrawal(100, "0x1")
            r2 = await v.request_withdrawal(200, "0x2")
            assert r1.nonce == 0
            assert r2.nonce == 1
        run(_test())

    def test_approve_withdrawal_signs(self):
        async def _test():
            transport = InMemoryTransport()
            v1 = await _make_validator("v1", transport)
            v2 = await _make_validator("v2", transport)
            await v1.join_bridge()
            await v2.join_bridge()
            rec = await v1.request_withdrawal(100, "0xeth")
            sig = await v2.approve_withdrawal(rec.nonce)
            assert isinstance(sig, bytes)
            assert len(sig) == 32
        run(_test())

    def test_approve_withdrawal_unknown_raises(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            with pytest.raises(KeyError, match="Unknown withdrawal"):
                await v.approve_withdrawal(999)
        run(_test())

    def test_collect_approvals_threshold(self):
        async def _test():
            transport = InMemoryTransport()
            v1 = await _make_validator("v1", transport, threshold=2, total=2)
            v2 = await _make_validator("v2", transport, threshold=2, total=2)
            await v1.join_bridge()
            await v2.join_bridge()
            rec = await v1.request_withdrawal(100, "0xeth")
            await v1.approve_withdrawal(rec.nonce)
            await v2.approve_withdrawal(rec.nonce)
            met, sigs = await v1.collect_approvals(rec.nonce)
            assert met is True
            assert len(sigs) >= 2
        run(_test())

    def test_send_heartbeat_no_crash(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            await v.send_heartbeat()
            # Verify DHT was written
            key = BridgeProtocol.bridge_validator_key(v.did)
            raw = await v.client.dht_get(key)
            assert raw is not None
            assert raw["state"] == "active"
        run(_test())

    def test_emergency_halt_sets_state(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            await v.emergency_halt("test reason")
            assert v.state == BridgeState.HALTED
        run(_test())

    def test_emergency_halt_prevents_operations(self):
        async def _test():
            v = await _make_validator()
            await v.join_bridge()
            await v.emergency_halt("panic")
            with pytest.raises(RuntimeError, match="halted"):
                await v.observe_deposit("0xf", 1, 100, "0xs", "did:r")
            with pytest.raises(RuntimeError, match="halted"):
                await v.request_withdrawal(100, "0xeth")
        run(_test())

    def test_multiple_validators_attest_same_deposit(self):
        async def _test():
            transport = InMemoryTransport()
            validators = []
            for i in range(3):
                v = await _make_validator(f"v{i}", transport, threshold=3, total=3)
                await v.join_bridge()
                validators.append(v)

            await validators[0].observe_deposit("0xmulti", 10, 5000, "0xs", "did:r")
            for v in validators:
                await v.attest_deposit("0xmulti")

            met, sigs = await validators[0].collect_attestations("0xmulti")
            assert met is True
            assert len(sigs) == 3
        run(_test())

    def test_full_deposit_flow(self):
        """Full flow: observe → attest → collect (finalized)."""
        async def _test():
            transport = InMemoryTransport()
            v1 = await _make_validator("v1", transport, threshold=2, total=2)
            v2 = await _make_validator("v2", transport, threshold=2, total=2)
            await v1.join_bridge()
            await v2.join_bridge()

            # Observe
            rec = await v1.observe_deposit("0xfull", 42, 10000, "0xsender", "did:bob")
            assert not rec.finalized

            # Attest
            await v1.attest_deposit("0xfull")
            await v2.attest_deposit("0xfull")

            # Collect — should finalize
            met, sigs = await v1.collect_attestations("0xfull")
            assert met is True
            assert v1.deposits["0xfull"].finalized is True
        run(_test())
