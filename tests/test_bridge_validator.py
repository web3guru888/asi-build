"""
Bridge Validator Integration Tests
====================================

Multi-validator deposit/withdrawal flows and error scenarios.
All validators share a single InMemoryTransport so they see each
other's DHT writes — simulating a real network.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac

import pytest

from asi_build.rings.bridge.protocol import (
    BridgeProtocol,
    BridgeState,
    BridgeValidator,
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
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _make_validator(
    seed: str,
    transport: InMemoryTransport,
    threshold: int = 4,
    total: int = 6,
) -> BridgeValidator:
    """Create a connected BridgeValidator on the shared transport."""
    client = RingsClient(transport=transport)
    await client.connect()
    identity = MockIdentity(seed)
    return BridgeValidator(identity, client, threshold=threshold, total=total)


async def _make_validator_pool(
    n: int,
    threshold: int,
    transport: InMemoryTransport | None = None,
) -> list[BridgeValidator]:
    """Create n validators sharing one transport, all joined to the bridge."""
    t = transport or InMemoryTransport()
    validators = []
    for i in range(n):
        v = await _make_validator(f"validator-{i}", t, threshold=threshold, total=n)
        await v.join_bridge()
        validators.append(v)
    return validators


# ===================================================================
# 1.  Multi-Validator Deposit Flow (5 tests)
# ===================================================================


class TestMultiValidatorDeposit:
    """Multiple validators collaborating on a deposit flow."""

    def test_three_validators_observe_same_deposit(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(3, threshold=3, transport=transport)
            # All three observe the same deposit
            for v in vs:
                await v.observe_deposit("0xdep1", 100, 5000, "0xsender", "did:alice")
            # All should have the deposit locally
            for v in vs:
                assert "0xdep1" in v.deposits
        run(_test())

    def test_three_validators_attest_same_deposit(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(3, threshold=3, transport=transport)
            # Only v0 observes; others will discover via DHT in attest
            await vs[0].observe_deposit("0xdep2", 50, 1000, "0xsender", "did:bob")
            sigs = []
            for v in vs:
                sig = await v.attest_deposit("0xdep2")
                sigs.append(sig)
            # All signatures should be unique (different identity seeds)
            assert len(set(s.hex() for s in sigs)) == 3
        run(_test())

    def test_attestations_accumulate_in_dht(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(3, threshold=3, transport=transport)
            await vs[0].observe_deposit("0xdep3", 10, 500, "0xs", "did:r")
            for i, v in enumerate(vs):
                await v.attest_deposit("0xdep3")
                # After each attestation, DHT should have i+1 attestations
                raw = await v.client.dht_get(BridgeProtocol.bridge_deposit_key("0xdep3"))
                assert len(raw["attestations"]) == i + 1
        run(_test())

    def test_threshold_not_met_below(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(4, threshold=4, transport=transport)
            await vs[0].observe_deposit("0xdep4", 10, 100, "0xs", "did:r")
            # Only 3 of 4 attest
            for v in vs[:3]:
                await v.attest_deposit("0xdep4")
            met, sigs = await vs[0].collect_attestations("0xdep4")
            assert met is False
            assert len(sigs) == 3
        run(_test())

    def test_deposit_finalized_at_threshold(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(4, threshold=4, transport=transport)
            await vs[0].observe_deposit("0xdep5", 10, 100, "0xs", "did:r")
            for v in vs:
                await v.attest_deposit("0xdep5")
            met, sigs = await vs[0].collect_attestations("0xdep5")
            assert met is True
            assert len(sigs) == 4
            assert vs[0].deposits["0xdep5"].finalized is True
        run(_test())


# ===================================================================
# 2.  Multi-Validator Withdrawal Flow (5 tests)
# ===================================================================


class TestMultiValidatorWithdrawal:
    """Multiple validators collaborating on a withdrawal flow."""

    def test_validator_requests_withdrawal(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(3, threshold=2, transport=transport)
            rec = await vs[0].request_withdrawal(2000, "0xethaddr")
            assert rec.amount == 2000
            assert rec.requester_did == vs[0].did
            # Should be in DHT
            raw = await vs[0].client.dht_get(BridgeProtocol.bridge_withdrawal_key(rec.nonce))
            assert raw is not None
        run(_test())

    def test_other_validators_approve(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(3, threshold=2, transport=transport)
            rec = await vs[0].request_withdrawal(100, "0xeth")
            sig1 = await vs[1].approve_withdrawal(rec.nonce)
            sig2 = await vs[2].approve_withdrawal(rec.nonce)
            assert isinstance(sig1, bytes) and isinstance(sig2, bytes)
            assert sig1 != sig2  # different identities
        run(_test())

    def test_approvals_accumulate(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(3, threshold=3, transport=transport)
            rec = await vs[0].request_withdrawal(100, "0xeth")
            for i, v in enumerate(vs):
                await v.approve_withdrawal(rec.nonce)
                raw = await v.client.dht_get(BridgeProtocol.bridge_withdrawal_key(rec.nonce))
                assert len(raw["approvals"]) == i + 1
        run(_test())

    def test_withdrawal_threshold_check(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(3, threshold=3, transport=transport)
            rec = await vs[0].request_withdrawal(500, "0xeth")
            # Only 2 approve → not met
            await vs[0].approve_withdrawal(rec.nonce)
            await vs[1].approve_withdrawal(rec.nonce)
            met, sigs = await vs[0].collect_approvals(rec.nonce)
            assert met is False
            assert len(sigs) == 2
        run(_test())

    def test_withdrawal_executed_at_threshold(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(3, threshold=3, transport=transport)
            rec = await vs[0].request_withdrawal(500, "0xeth")
            for v in vs:
                await v.approve_withdrawal(rec.nonce)
            met, sigs = await vs[0].collect_approvals(rec.nonce)
            assert met is True
            assert len(sigs) == 3
            assert vs[0].withdrawals[rec.nonce].executed is True
        run(_test())


# ===================================================================
# 3.  Error Scenarios (5 tests)
# ===================================================================


class TestBridgeErrorScenarios:
    """Edge cases and error handling."""

    def test_double_attestation_by_same_validator(self):
        """Same validator attesting twice overwrites — should not double-count."""
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(2, threshold=2, transport=transport)
            await vs[0].observe_deposit("0xdup", 1, 100, "0xs", "did:r")
            await vs[0].attest_deposit("0xdup")
            await vs[0].attest_deposit("0xdup")  # same validator twice
            met, sigs = await vs[0].collect_attestations("0xdup")
            # Only 1 unique attestation (same DID key overwrites)
            assert len(sigs) == 1
            assert met is False
        run(_test())

    def test_attestation_after_emergency_halt(self):
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(2, threshold=2, transport=transport)
            await vs[0].observe_deposit("0xhalt", 1, 100, "0xs", "did:r")
            await vs[0].emergency_halt("suspicious activity")
            with pytest.raises(RuntimeError, match="halted"):
                await vs[0].attest_deposit("0xhalt")
        run(_test())

    def test_withdrawal_after_halt(self):
        """Cannot request withdrawal when halted."""
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(2, threshold=2, transport=transport)
            await vs[0].emergency_halt("test")
            with pytest.raises(RuntimeError, match="halted"):
                await vs[0].request_withdrawal(100, "0xeth")
        run(_test())

    def test_approve_nonexistent_nonce(self):
        """Approving a withdrawal that doesn't exist raises KeyError."""
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(2, threshold=2, transport=transport)
            with pytest.raises(KeyError, match="Unknown withdrawal"):
                await vs[0].approve_withdrawal(12345)
        run(_test())

    def test_collect_attestations_unknown_deposit(self):
        """Collecting attestations for a non-existent deposit → (False, [])."""
        async def _test():
            transport = InMemoryTransport()
            vs = await _make_validator_pool(2, threshold=2, transport=transport)
            met, sigs = await vs[0].collect_attestations("0xghost")
            assert met is False
            assert sigs == []
        run(_test())
