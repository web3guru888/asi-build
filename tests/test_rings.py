"""
Tests for Rings Network SDK and Blackboard Adapter
=====================================================

Covers:
- RingsClient:        DHT, Chord ring, Sub-Rings, sessions, connection lifecycle
- RingsDID:           DID creation, resolution, proof generation/verification, VIDs
- ReputationClient:   Local scoring, trust tiers, slash reports, median game
- RingsNetworkAdapter: Blackboard integration, event emission, production sweep
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import pytest

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from asi_build.rings.client import (
    ConnectionState,
    DHTOperator,
    FingerEntry,
    InMemoryTransport,
    PeerInfo,
    RingsClient,
    SessionInfo,
    SubRingInfo,
    _compute_vid,
    _did_to_position,
    RING_MODULUS,
)
from asi_build.rings.did import (
    DIDDocument,
    DIDKeyPair,
    DIDProof,
    KeyCurve,
    RingsDID,
    VerificationType,
)
from asi_build.rings.reputation import (
    BehaviourType,
    GlobalRankRecord,
    LocalObservation,
    LocalRankRecord,
    ReputationClient,
    SlashReport,
    TrustTier,
)
from asi_build.integration.adapters.rings_adapter import (
    RingsNetworkAdapter,
    DEFAULT_TOPIC_SUBRING_MAP,
)
from asi_build.integration.protocols import (
    BlackboardEntry,
    CognitiveEvent,
    EntryPriority,
    ModuleCapability,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(coro):
    """Run an async coroutine synchronously (for tests without pytest-asyncio)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class MockBlackboard:
    """Minimal mock of CognitiveBlackboard for adapter testing."""

    def __init__(self):
        self.registered_modules: List[Any] = []
        self.posted_entries: List[BlackboardEntry] = []
        self._event_bus = MockEventBus()

    @property
    def event_bus(self):
        return self._event_bus

    def register_module(self, adapter):
        self.registered_modules.append(adapter)
        if hasattr(adapter, "on_registered"):
            adapter.on_registered(self)

    def post(self, topic: str, data: Any):
        entry = BlackboardEntry(topic=topic, data=data, source_module="mock")
        self.posted_entries.append(entry)
        return entry.entry_id

    def post_many(self, entries):
        ids = []
        for e in entries:
            self.posted_entries.append(e)
            ids.append(e.entry_id)
        return ids


class MockEventBus:
    """Minimal mock of EventBus."""

    def __init__(self):
        self.emitted: List[CognitiveEvent] = []
        self.subscriptions: List[Dict[str, Any]] = []

    def emit(self, event: CognitiveEvent) -> int:
        self.emitted.append(event)
        return 1

    def subscribe(self, pattern: str, handler=None, source_filter=None, **kw):
        self.subscriptions.append({
            "pattern": pattern,
            "handler": handler,
            "source_filter": source_filter,
        })
        return "sub_mock"


# ===========================================================================
# RingsClient tests
# ===========================================================================


class TestRingsClientConnection:
    """Connection lifecycle tests."""

    def test_initial_state_disconnected(self):
        client = RingsClient()
        assert client.state == ConnectionState.DISCONNECTED
        assert not client.is_connected
        assert client.local_did is None

    def test_connect_succeeds(self):
        client = RingsClient()
        run(client.connect())
        assert client.state == ConnectionState.CONNECTED
        assert client.is_connected
        assert client.local_did is not None

    def test_disconnect(self):
        client = RingsClient()
        run(client.connect())
        run(client.disconnect())
        assert client.state == ConnectionState.DISCONNECTED
        assert not client.is_connected

    def test_double_connect_idempotent(self):
        client = RingsClient()
        run(client.connect())
        run(client.connect())  # Should not raise
        assert client.is_connected

    def test_double_disconnect_idempotent(self):
        client = RingsClient()
        run(client.disconnect())  # Should not raise
        assert client.state == ConnectionState.DISCONNECTED

    def test_context_manager(self):
        async def _run():
            async with RingsClient() as client:
                assert client.is_connected
                return client.state
        result = run(_run())
        assert result == ConnectionState.CONNECTED

    def test_endpoint_property(self):
        client = RingsClient("ws://custom:9999")
        assert client.endpoint == "ws://custom:9999"

    def test_transport_property(self):
        client = RingsClient()
        assert isinstance(client.transport, InMemoryTransport)

    def test_repr(self):
        client = RingsClient()
        r = repr(client)
        assert "RingsClient" in r
        assert "disconnected" in r


class TestRingsClientDHT:
    """DHT operations."""

    def test_put_and_get(self):
        async def _run():
            async with RingsClient() as c:
                await c.dht_put("key1", {"value": 42})
                result = await c.dht_get("key1")
                return result
        assert run(_run()) == {"value": 42}

    def test_get_nonexistent_returns_none(self):
        async def _run():
            async with RingsClient() as c:
                return await c.dht_get("nonexistent")
        assert run(_run()) is None

    def test_put_overwrite(self):
        async def _run():
            async with RingsClient() as c:
                await c.dht_put("key1", "v1")
                await c.dht_put("key1", "v2")
                return await c.dht_get("key1")
        assert run(_run()) == "v2"

    def test_put_extend(self):
        async def _run():
            async with RingsClient() as c:
                await c.dht_put("key1", "v1")
                await c.dht_put("key1", "v2", operator=DHTOperator.EXTEND)
                result = await c.dht_get("key1")
                return result
        result = run(_run())
        assert isinstance(result, list)
        assert "v1" in result and "v2" in result

    def test_delete(self):
        async def _run():
            async with RingsClient() as c:
                await c.dht_put("key1", "v1")
                await c.dht_delete("key1")
                return await c.dht_get("key1")
        assert run(_run()) is None


class TestRingsClientRing:
    """Chord ring operations."""

    def test_join_ring(self):
        async def _run():
            async with RingsClient() as c:
                info = await c.join_ring()
                return info
        info = run(_run())
        assert isinstance(info, PeerInfo)
        assert info.did != ""

    def test_find_successor(self):
        async def _run():
            async with RingsClient() as c:
                result = await c.find_successor(12345)
                return result
        result = run(_run())
        assert isinstance(result, PeerInfo)
        assert result.position == 12345 % RING_MODULUS

    def test_get_finger_table(self):
        async def _run():
            async with RingsClient() as c:
                table = await c.get_finger_table()
                return table
        table = run(_run())
        assert len(table) == 160
        assert all(isinstance(e, FingerEntry) for e in table)
        assert table[0].index == 0

    def test_get_peers(self):
        async def _run():
            async with RingsClient() as c:
                await c.join_ring()
                return await c.get_peers()
        peers = run(_run())
        assert isinstance(peers, list)


class TestRingsClientSubRing:
    """Sub-Ring operations."""

    def test_create_sub_ring(self):
        async def _run():
            async with RingsClient() as c:
                info = await c.create_sub_ring("test-topic")
                return info
        info = run(_run())
        assert isinstance(info, SubRingInfo)
        assert info.topic == "test-topic"
        assert info.vid.startswith("vid:")
        assert info.joined

    def test_join_sub_ring(self):
        async def _run():
            async with RingsClient() as c:
                info = await c.join_sub_ring("test-topic")
                return info
        info = run(_run())
        assert info.joined
        assert info.topic == "test-topic"

    def test_leave_sub_ring(self):
        async def _run():
            async with RingsClient() as c:
                await c.join_sub_ring("test-topic")
                await c.leave_sub_ring("test-topic")
        run(_run())  # Should not raise

    def test_get_sub_ring_members(self):
        async def _run():
            async with RingsClient() as c:
                await c.join_sub_ring("test-topic")
                members = await c.get_sub_ring_members("test-topic")
                return members
        members = run(_run())
        assert isinstance(members, list)

    def test_broadcast(self):
        async def _run():
            async with RingsClient() as c:
                await c.create_sub_ring("news")
                result = await c.broadcast("news", {"msg": "hello"})
                return result
        result = run(_run())
        assert result["ok"] is True
        assert "recipients" in result


class TestRingsClientSession:
    """E2E session management."""

    def test_create_session(self):
        async def _run():
            async with RingsClient() as c:
                session = await c.create_session("did:rings:peer1")
                return session
        s = run(_run())
        assert isinstance(s, SessionInfo)
        assert s.peer_did == "did:rings:peer1"
        assert s.session_id != ""

    def test_send_and_receive(self):
        async def _run():
            async with RingsClient() as c:
                s = await c.create_session("did:rings:peer1")
                await c.session_send(s.session_id, {"msg": "hello"})
                # Mock transport stores outbound; receive returns None (no inbound)
                result = await c.session_receive(s.session_id)
                return result
        assert run(_run()) is None  # No inbound messages in mock

    def test_close_session(self):
        async def _run():
            async with RingsClient() as c:
                s = await c.create_session("did:rings:peer1")
                await c.close_session(s.session_id)
        run(_run())  # Should not raise


class TestRingsClientDIDResolution:
    """DID resolution via the client."""

    def test_resolve_unknown_did_returns_none(self):
        async def _run():
            async with RingsClient() as c:
                return await c.resolve_did("did:rings:unknown")
        assert run(_run()) is None

    def test_resolve_known_did(self):
        async def _run():
            async with RingsClient() as c:
                # Join ring first to register the DID
                await c.join_ring()
                doc = await c.resolve_did(c.local_did)
                return doc
        doc = run(_run())
        assert doc is not None
        assert "verificationMethod" in doc


class TestRingsClientHelpers:
    """Static helper methods."""

    def test_compute_vid(self):
        vid = RingsClient.compute_vid("test-name")
        assert vid.startswith("vid:")
        # Deterministic
        assert vid == RingsClient.compute_vid("test-name")
        # Different input → different vid
        assert vid != RingsClient.compute_vid("other-name")

    def test_did_to_position(self):
        pos = RingsClient.did_to_position("did:rings:ed25519:abc")
        assert 0 <= pos < RING_MODULUS
        # Deterministic
        assert pos == RingsClient.did_to_position("did:rings:ed25519:abc")

    def test_vid_helper_matches_module(self):
        assert _compute_vid("x") == RingsClient.compute_vid("x")


# ===========================================================================
# RingsDID tests
# ===========================================================================


class TestDIDKeyPair:
    """Key pair generation."""

    def test_generate_secp256k1(self):
        kp = DIDKeyPair.generate(KeyCurve.SECP256K1)
        assert kp.curve == KeyCurve.SECP256K1
        # secp256k1: uncompressed public key = 65 bytes → 130 hex chars
        assert len(kp.public_key_hex) == 130
        # secp256k1: private key scalar = 32 bytes → 64 hex chars
        assert len(kp.private_key_hex) == 64
        assert kp.key_id.startswith("key-")

    def test_generate_ed25519(self):
        kp = DIDKeyPair.generate(KeyCurve.ED25519)
        assert kp.curve == KeyCurve.ED25519

    def test_deterministic_with_seed(self):
        kp1 = DIDKeyPair.generate(seed="test-seed-123")
        kp2 = DIDKeyPair.generate(seed="test-seed-123")
        assert kp1.public_key_hex == kp2.public_key_hex
        assert kp1.private_key_hex == kp2.private_key_hex

    def test_different_seeds_produce_different_keys(self):
        kp1 = DIDKeyPair.generate(seed="seed-a")
        kp2 = DIDKeyPair.generate(seed="seed-b")
        assert kp1.public_key_hex != kp2.public_key_hex


class TestRingsDIDCreation:
    """DID creation and management."""

    def test_create_did_default_curve(self):
        mgr = RingsDID()
        did, doc = mgr.create_did()
        assert did.startswith("did:rings:secp256k1:")
        assert doc.did == did
        assert len(doc.verification_methods) == 1
        assert doc.verification_methods[0]["type"] == VerificationType.ECDSA_SECP256K1.value

    def test_create_did_ed25519(self):
        mgr = RingsDID()
        did, doc = mgr.create_did(curve=KeyCurve.ED25519)
        assert did.startswith("did:rings:ed25519:")
        assert doc.verification_methods[0]["type"] == VerificationType.ED25519.value

    def test_create_did_deterministic(self):
        mgr = RingsDID()
        did1, _ = mgr.create_did(seed="test")
        mgr2 = RingsDID()
        did2, _ = mgr2.create_did(seed="test")
        assert did1 == did2

    def test_create_did_with_services(self):
        mgr = RingsDID()
        services = [{"id": "svc-1", "type": "TestService", "serviceEndpoint": "http://x"}]
        did, doc = mgr.create_did(services=services)
        assert len(doc.services) == 1
        assert doc.services[0]["type"] == "TestService"

    def test_list_local_dids(self):
        mgr = RingsDID()
        mgr.create_did(seed="a")
        mgr.create_did(seed="b")
        dids = mgr.list_local_dids()
        assert len(dids) == 2

    def test_get_key_pair(self):
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="test")
        kp = mgr.get_key_pair(did)
        assert kp is not None
        assert kp.curve == KeyCurve.SECP256K1

    def test_get_key_pair_unknown_returns_none(self):
        mgr = RingsDID()
        assert mgr.get_key_pair("did:rings:unknown:xxx") is None


class TestRingsDIDProof:
    """Proof generation and verification."""

    def test_create_proof(self):
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="proof-test")
        proof = mgr.create_proof(did, challenge="nonce-123")
        assert proof.challenge == "nonce-123"
        assert proof.signature != ""
        # ECDSA DER signature is variable length (typically 138–144 hex chars)
        assert len(proof.signature) >= 128
        assert proof.verification_method != ""

    def test_verify_proof_succeeds(self):
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="verify-test")
        proof = mgr.create_proof(did, challenge="c1", domain="test.com")
        assert mgr.verify_proof(did, proof) is True

    def test_verify_proof_fails_with_wrong_challenge(self):
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="verify-test")
        proof = mgr.create_proof(did, challenge="c1")
        # Tamper with the challenge
        proof.challenge = "c2"
        assert mgr.verify_proof(did, proof) is False

    def test_verify_proof_fails_with_tampered_signature(self):
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="verify-test")
        proof = mgr.create_proof(did, challenge="c1")
        proof.signature = "0" * 64
        assert mgr.verify_proof(did, proof) is False

    def test_create_proof_unknown_did_raises(self):
        mgr = RingsDID()
        with pytest.raises(ValueError, match="No local key"):
            mgr.create_proof("did:rings:unknown:xxx")

    def test_proof_types(self):
        mgr = RingsDID()
        did_secp, _ = mgr.create_did(curve=KeyCurve.SECP256K1, seed="s1")
        did_ed, _ = mgr.create_did(curve=KeyCurve.ED25519, seed="s2")
        p1 = mgr.create_proof(did_secp)
        p2 = mgr.create_proof(did_ed)
        assert "secp256k1" in p1.proof_type.lower() or "Secp256k1" in p1.proof_type
        assert "ed25519" in p2.proof_type.lower() or "Ed25519" in p2.proof_type


class TestRingsDIDResolution:
    """DID resolution (local + network)."""

    def test_resolve_local(self):
        mgr = RingsDID()
        did, expected_doc = mgr.create_did(seed="r1")
        doc = mgr.resolve_local(did)
        assert doc is not None
        assert doc.did == did

    def test_resolve_local_unknown_returns_none(self):
        mgr = RingsDID()
        assert mgr.resolve_local("did:rings:unknown:xxx") is None

    def test_resolve_async_local_hit(self):
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="r2")
        doc = run(mgr.resolve(did))
        assert doc is not None
        assert doc.did == did

    def test_resolve_async_network_hit(self):
        """Test resolution via network (mock client)."""
        async def _run():
            async with RingsClient() as c:
                # Register a peer so resolution works
                await c.join_ring()
                mgr = RingsDID(client=c)
                doc = await mgr.resolve(c.local_did)
                return doc
        doc = run(_run())
        assert doc is not None


class TestRingsDIDVirtualIDs:
    """Virtual DID computation."""

    def test_compute_vid(self):
        vid = RingsDID.compute_vid("data", "my-key")
        assert vid.startswith("vid:")
        # Deterministic
        assert vid == RingsDID.compute_vid("data", "my-key")

    def test_compute_vid_different_namespace(self):
        v1 = RingsDID.compute_vid("data", "key")
        v2 = RingsDID.compute_vid("mailto", "key")
        assert v1 != v2

    def test_vid_to_position(self):
        vid = RingsDID.compute_vid("test", "abc")
        pos = RingsDID.vid_to_position(vid)
        assert 0 <= pos < RING_MODULUS


class TestDIDDocument:
    """DID Document serialization."""

    def test_to_dict(self):
        mgr = RingsDID()
        did, doc = mgr.create_did(seed="ser")
        d = doc.to_dict()
        assert d["id"] == did
        assert "@context" in d
        assert len(d["verificationMethod"]) == 1

    def test_from_dict_roundtrip(self):
        mgr = RingsDID()
        did, doc = mgr.create_did(seed="rt")
        d = doc.to_dict()
        restored = DIDDocument.from_dict(d)
        assert restored.did == did
        assert len(restored.verification_methods) == 1

    def test_add_service(self):
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="svc")
        mgr.add_service(did, "training", "ASIBuildTrainingNode", "ws://x:5000")
        doc = mgr.resolve_local(did)
        assert len(doc.services) == 1
        assert doc.services[0]["type"] == "ASIBuildTrainingNode"

    def test_add_service_unknown_did_raises(self):
        mgr = RingsDID()
        with pytest.raises(ValueError, match="No local document"):
            mgr.add_service("did:rings:unknown:x", "svc", "Type", "url")


# ===========================================================================
# ReputationClient tests
# ===========================================================================


class TestReputationScoring:
    """Local scoring and rank computation."""

    def test_initial_state(self):
        rep = ReputationClient(local_did="did:me")
        assert rep.peer_count == 0
        assert rep.total_observations == 0
        assert rep.local_did == "did:me"

    def test_report_behaviour(self):
        rep = ReputationClient()
        obs = rep.report_behaviour("did:peer1", BehaviourType.REQUEST_SUCCESS, 0.9)
        assert isinstance(obs, LocalObservation)
        assert obs.peer_did == "did:peer1"
        assert obs.score == 0.9
        assert rep.peer_count == 1
        assert rep.total_observations == 1

    def test_local_rank_computed(self):
        rep = ReputationClient()
        rep.report_behaviour("did:p1", BehaviourType.REQUEST_SUCCESS, 0.9)
        rank = rep.get_local_rank("did:p1")
        assert rank is not None
        assert rank.peer_did == "did:p1"
        assert rank.score > 0

    def test_multiple_observations_aggregated(self):
        rep = ReputationClient()
        for _ in range(5):
            rep.report_behaviour("did:p1", BehaviourType.REQUEST_SUCCESS, 0.8)
        for _ in range(5):
            rep.report_behaviour("did:p1", BehaviourType.REQUEST_FAILURE, 0.2)
        rank = rep.get_local_rank("did:p1")
        # Score should reflect mixed performance
        assert 0.2 < rank.score < 0.8

    def test_score_clamped(self):
        rep = ReputationClient()
        obs = rep.report_behaviour("did:p1", BehaviourType.REQUEST_SUCCESS, 1.5)
        assert obs.score == 1.0
        obs2 = rep.report_behaviour("did:p1", BehaviourType.REQUEST_FAILURE, -0.5)
        assert obs2.score == 0.0

    def test_get_local_score_unknown(self):
        rep = ReputationClient()
        assert rep.get_local_score("did:unknown") == 0.0

    def test_get_all_local_ranks(self):
        rep = ReputationClient()
        rep.report_behaviour("did:a", BehaviourType.REQUEST_SUCCESS, 0.9)
        rep.report_behaviour("did:b", BehaviourType.REQUEST_SUCCESS, 0.5)
        ranks = rep.get_all_local_ranks()
        assert len(ranks) == 2
        assert "did:a" in ranks and "did:b" in ranks

    def test_get_top_peers(self):
        rep = ReputationClient()
        rep.report_behaviour("did:a", BehaviourType.REQUEST_SUCCESS, 0.9)
        rep.report_behaviour("did:b", BehaviourType.REQUEST_SUCCESS, 0.5)
        rep.report_behaviour("did:c", BehaviourType.REQUEST_SUCCESS, 0.7)
        top = rep.get_top_peers(n=2)
        assert len(top) == 2
        assert top[0].score >= top[1].score


class TestReputationTrust:
    """Trust tier and threshold checks."""

    def test_trust_tier_mapping(self):
        assert TrustTier.from_score(0.0) == TrustTier.UNTRUSTED
        assert TrustTier.from_score(0.1) == TrustTier.UNTRUSTED
        assert TrustTier.from_score(0.2) == TrustTier.LOW
        assert TrustTier.from_score(0.4) == TrustTier.MEDIUM
        assert TrustTier.from_score(0.6) == TrustTier.HIGH
        assert TrustTier.from_score(0.8) == TrustTier.VERIFIED
        assert TrustTier.from_score(1.0) == TrustTier.VERIFIED

    def test_is_trustworthy_local(self):
        rep = ReputationClient()
        rep.report_behaviour("did:good", BehaviourType.REQUEST_SUCCESS, 0.9)
        rep.report_behaviour("did:bad", BehaviourType.REQUEST_FAILURE, 0.1)
        assert rep.is_trustworthy_local("did:good", threshold=0.3)
        assert not rep.is_trustworthy_local("did:bad", threshold=0.3)

    def test_is_trustworthy_local_default_threshold(self):
        rep = ReputationClient(default_threshold=0.8)
        # Single REQUEST_SUCCESS(0.4): composite = 0.4*1.0 + 0.3*0.5 + 0.3*0.4 = 0.67
        rep.report_behaviour("did:mid", BehaviourType.REQUEST_SUCCESS, 0.4)
        assert not rep.is_trustworthy_local("did:mid")

    def test_get_trust_tier(self):
        rep = ReputationClient()
        rep.report_behaviour("did:high", BehaviourType.REQUEST_SUCCESS, 0.95)
        tier = rep.get_trust_tier("did:high")
        assert tier in (TrustTier.HIGH, TrustTier.VERIFIED)

    def test_is_trustworthy_async(self):
        rep = ReputationClient()
        rep.report_behaviour("did:p", BehaviourType.REQUEST_SUCCESS, 0.8)
        result = run(rep.is_trustworthy("did:p", threshold=0.3))
        assert result is True


class TestReputationSlash:
    """Slash reports."""

    def test_slash_report(self):
        rep = ReputationClient(local_did="did:me")
        report = rep.report_slash("did:evil", "poisoned gradients")
        assert isinstance(report, SlashReport)
        assert report.target_did == "did:evil"
        assert report.reporter_did == "did:me"
        assert report.reason == "poisoned gradients"

    def test_slash_lowers_score(self):
        rep = ReputationClient()
        # Build up positive rep
        for _ in range(10):
            rep.report_behaviour("did:p", BehaviourType.REQUEST_SUCCESS, 0.9)
        score_before = rep.get_local_score("did:p")
        # Slash
        rep.report_slash("did:p", "bad behaviour")
        score_after = rep.get_local_score("did:p")
        assert score_after < score_before


class TestReputationMedianGame:
    """Median game reward computation."""

    def test_exact_median(self):
        reward = ReputationClient.median_game_reward([0.3, 0.5, 0.7], 0.5)
        assert reward == pytest.approx(1.0, abs=0.01)

    def test_far_from_median(self):
        reward = ReputationClient.median_game_reward([0.3, 0.5, 0.7], 0.0)
        assert reward < 0.5

    def test_empty_scores(self):
        assert ReputationClient.median_game_reward([], 0.5) == 0.0


class TestReputationStatistics:
    """Network statistics computation."""

    def test_empty_stats(self):
        rep = ReputationClient()
        stats = rep.compute_network_statistics()
        assert stats["peer_count"] == 0
        assert stats["mean_score"] == 0.0

    def test_stats_with_data(self):
        rep = ReputationClient()
        rep.report_behaviour("did:a", BehaviourType.REQUEST_SUCCESS, 0.9)
        rep.report_behaviour("did:b", BehaviourType.REQUEST_SUCCESS, 0.5)
        stats = rep.compute_network_statistics()
        assert stats["peer_count"] == 2
        assert stats["mean_score"] > 0

    def test_get_state(self):
        rep = ReputationClient(local_did="did:me")
        rep.report_behaviour("did:p", BehaviourType.REQUEST_SUCCESS, 0.8)
        state = rep.get_state()
        assert state["local_did"] == "did:me"
        assert "did:p" in state["local_ranks"]


class TestReputationRepr:
    def test_repr(self):
        rep = ReputationClient(local_did="did:me")
        r = repr(rep)
        assert "ReputationClient" in r
        assert "did:me" in r


# ===========================================================================
# RingsNetworkAdapter tests
# ===========================================================================


class TestAdapterRegistration:
    """Adapter registration and module info."""

    def test_module_info(self):
        adapter = RingsNetworkAdapter()
        info = adapter.module_info
        assert info.name == "rings_network"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert ModuleCapability.TRANSFORMER in info.capabilities
        assert "rings.peer" in info.topics_produced
        assert "rings.did" in info.topics_produced
        assert "rings.reputation" in info.topics_produced
        assert "reasoning" in info.topics_consumed

    def test_registration_with_blackboard(self):
        adapter = RingsNetworkAdapter()
        bb = MockBlackboard()
        bb.register_module(adapter)
        assert adapter._blackboard is bb
        assert len(bb.registered_modules) == 1

    def test_event_handler_wiring(self):
        adapter = RingsNetworkAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("test.event", {"key": "value"})
        assert len(events) == 1
        assert events[0].event_type == "test.event"


class TestAdapterPeerDiscovery:
    """Peer discovery and DID authentication recording."""

    def test_record_peer_discovery(self):
        adapter = RingsNetworkAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))

        entry = adapter.record_peer_discovery(
            "did:rings:ed25519:abc", position=42, capabilities={"gpu": True}
        )
        assert entry.topic == "rings.peer.discovered"
        assert entry.data["peer_did"] == "did:rings:ed25519:abc"
        assert entry.data["position"] == 42
        assert "peer" in entry.tags
        assert len(events) == 1
        assert events[0].event_type == "rings.peer.discovered"

    def test_record_did_auth_success(self):
        adapter = RingsNetworkAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))

        entry = adapter.record_did_authentication(
            "did:rings:ed25519:abc", success=True, trust_tier="high"
        )
        assert entry.topic == "rings.did.authenticated"
        assert entry.data["authenticated"] is True
        assert entry.confidence > 0.9
        assert "did:rings:ed25519:abc" in adapter._authenticated_peers

    def test_record_did_auth_failure(self):
        adapter = RingsNetworkAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))

        entry = adapter.record_did_authentication("did:evil", success=False)
        assert entry.topic == "rings.did.failed"
        assert entry.priority == EntryPriority.HIGH  # Failures are high priority
        assert "did:evil" not in adapter._authenticated_peers


class TestAdapterReputation:
    """Reputation recording and threshold detection."""

    def test_record_reputation_update(self):
        adapter = RingsNetworkAdapter()
        entry = adapter.record_reputation_update("did:p1", 0.7)
        assert entry.topic == "rings.reputation.updated"
        assert entry.data["score"] == 0.7

    def test_reputation_threshold_crossing_up(self):
        adapter = RingsNetworkAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))

        # Set below threshold first
        adapter.record_reputation_update("did:p1", 0.3, previous_score=0.3)
        events.clear()

        # Cross above threshold
        adapter.record_reputation_update("did:p1", 0.6, previous_score=0.3)
        threshold_events = [e for e in events if "threshold_crossed" in e.event_type]
        assert len(threshold_events) == 1
        assert threshold_events[0].payload["direction"] == "up"

    def test_reputation_threshold_crossing_down(self):
        adapter = RingsNetworkAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))

        adapter._reputation_cache["did:p1"] = 0.7
        adapter.record_reputation_update("did:p1", 0.3)
        threshold_events = [e for e in events if "threshold_crossed" in e.event_type]
        assert len(threshold_events) == 1
        assert threshold_events[0].payload["direction"] == "down"

    def test_record_slash(self):
        rep = ReputationClient(local_did="did:me")
        adapter = RingsNetworkAdapter(reputation=rep)
        entry = adapter.record_slash("did:bad", "data poisoning", {"proof": "xxx"})
        assert entry.topic == "rings.reputation.slash"
        assert entry.data["target_did"] == "did:bad"
        assert "security" in entry.tags


class TestAdapterSubRing:
    """Sub-Ring event recording."""

    def test_record_subring_join(self):
        adapter = RingsNetworkAdapter()
        entry = adapter.record_subring_join("asi-build:reasoning", member_count=5)
        assert entry.topic == "rings.subring.joined"
        assert "asi-build:reasoning" in adapter._joined_subrings

    def test_record_subring_message(self):
        adapter = RingsNetworkAdapter()
        entry = adapter.record_subring_message(
            "asi-build:kg", {"triple": "s p o"}, sender_did="did:p1"
        )
        assert entry.topic == "rings.subring.message"
        assert entry.data["sender_did"] == "did:p1"


class TestAdapterProduceSweep:
    """Production sweep."""

    def test_produce_network_status(self):
        adapter = RingsNetworkAdapter()
        entries = adapter.produce()
        # First call should produce a status entry
        status = [e for e in entries if e.topic == "rings.network.status"]
        assert len(status) == 1
        assert "connected" in status[0].data

    def test_produce_no_change_skips(self):
        adapter = RingsNetworkAdapter()
        entries1 = adapter.produce()
        entries2 = adapter.produce()
        # Second call should not produce status (no change)
        status2 = [e for e in entries2 if e.topic == "rings.network.status"]
        assert len(status2) == 0

    def test_produce_reputation_changes(self):
        rep = ReputationClient()
        rep.report_behaviour("did:a", BehaviourType.REQUEST_SUCCESS, 0.8)
        adapter = RingsNetworkAdapter(reputation=rep)
        entries = adapter.produce()
        rep_entries = [e for e in entries if e.topic == "rings.reputation.updated"]
        assert len(rep_entries) == 1


class TestAdapterConsume:
    """Entry consumption."""

    def test_consume_reasoning_entry(self):
        adapter = RingsNetworkAdapter()
        entry = BlackboardEntry(
            topic="reasoning.inference",
            data={"result": "x"},
            source_module="reasoning",
        )
        adapter.consume([entry])  # Should not raise

    def test_consume_unknown_topic_skipped(self):
        adapter = RingsNetworkAdapter()
        entry = BlackboardEntry(
            topic="unknown.topic",
            data={},
            source_module="test",
        )
        adapter.consume([entry])  # Should not raise


class TestAdapterEventHandling:
    """Event listener."""

    def test_handle_event_without_client(self):
        adapter = RingsNetworkAdapter(client=None)
        event = CognitiveEvent(event_type="reasoning.inference.completed", payload={})
        adapter.handle_event(event)  # Should not raise (graceful)

    def test_handle_event_with_joined_subring(self):
        client = RingsClient()
        adapter = RingsNetworkAdapter(client=client)
        adapter._joined_subrings.add("asi-build:reasoning")
        event = CognitiveEvent(
            event_type="reasoning.inference.completed",
            payload={"result": "found!"},
        )
        adapter.handle_event(event)  # Should schedule broadcast


class TestAdapterTransform:
    """Entry transformation (reputation enrichment)."""

    def test_transform_without_reputation(self):
        adapter = RingsNetworkAdapter(reputation=None)
        entry = BlackboardEntry(topic="test", data={}, source_module="test")
        result = adapter.transform([entry])
        assert result == []

    def test_transform_with_matching_reputation(self):
        rep = ReputationClient()
        adapter = RingsNetworkAdapter(reputation=rep)
        # Cache a score for a "module" that matches
        adapter._reputation_cache["did:reasoning_module"] = 0.85
        entry = BlackboardEntry(
            topic="reasoning.inference",
            data={"x": 1},
            source_module="reasoning_module",
        )
        result = adapter.transform([entry])
        # Should match because "reasoning_module" is in the cached DID
        assert len(result) == 1
        assert result[0].metadata.get("rings_reputation") == 0.85
        assert "rings-enriched" in result[0].tags


class TestAdapterSnapshot:
    """Diagnostic snapshot."""

    def test_snapshot(self):
        adapter = RingsNetworkAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "rings_network"
        assert snap["connected"] is False
        assert snap["has_client"] is False
        assert isinstance(snap["topic_subring_map"], dict)

    def test_set_connected(self):
        adapter = RingsNetworkAdapter()
        adapter.set_connected(True)
        assert adapter._connected is True
        snap = adapter.snapshot()
        assert snap["connected"] is True


class TestAdapterGracefulDegradation:
    """Adapter works with all components set to None."""

    def test_all_none_produce(self):
        adapter = RingsNetworkAdapter(client=None, did_manager=None, reputation=None)
        entries = adapter.produce()
        # Should still produce status
        assert any(e.topic == "rings.network.status" for e in entries)

    def test_all_none_consume(self):
        adapter = RingsNetworkAdapter(client=None, did_manager=None, reputation=None)
        entry = BlackboardEntry(topic="reasoning.x", data={}, source_module="r")
        adapter.consume([entry])  # Should not raise

    def test_all_none_handle_event(self):
        adapter = RingsNetworkAdapter(client=None)
        event = CognitiveEvent(event_type="reasoning.x", payload={})
        adapter.handle_event(event)  # Should not raise


# ===========================================================================
# Integration: SDK + Adapter together
# ===========================================================================


class TestEndToEnd:
    """End-to-end flow: create DID, score reputation, wire adapter."""

    def test_full_flow(self):
        """Test creating a DID, checking reputation, and recording events."""
        # 1. Create DID
        did_mgr = RingsDID()
        did, doc = did_mgr.create_did(seed="e2e-test")

        # 2. Create proof and verify
        proof = did_mgr.create_proof(did, challenge="e2e-challenge")
        assert did_mgr.verify_proof(did, proof)

        # 3. Build reputation
        rep = ReputationClient(local_did=did)
        peer = "did:rings:ed25519:peer1"
        for _ in range(5):
            rep.report_behaviour(peer, BehaviourType.REQUEST_SUCCESS, 0.85)
        assert rep.is_trustworthy_local(peer, threshold=0.5)

        # 4. Wire adapter
        adapter = RingsNetworkAdapter(
            did_manager=did_mgr,
            reputation=rep,
        )
        bb = MockBlackboard()
        bb.register_module(adapter)

        # 5. Record events
        disc_entry = adapter.record_peer_discovery(peer)
        auth_entry = adapter.record_did_authentication(peer, success=True, trust_tier="high")

        # 6. Production sweep
        entries = adapter.produce()
        assert len(entries) >= 1  # At least network status
