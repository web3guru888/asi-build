"""
Tests for Rings DID module with real secp256k1 / ed25519 cryptography.

Covers: key generation, DID creation, proof generation & verification,
VID computation, service registration, and edge cases.
"""

import asyncio
import hashlib

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519

from asi_build.rings.did import (
    DIDDocument,
    DIDKeyPair,
    DIDProof,
    KeyCurve,
    RingsDID,
    RING_MODULUS,
    VerificationType,
    _private_key_from_hex,
    _public_key_from_hex,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Key Generation (10 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestKeyGeneration:
    """DIDKeyPair.generate() with real keys."""

    def test_secp256k1_public_key_length(self):
        """Uncompressed secp256k1 public key is 130 hex chars (65 bytes)."""
        kp = DIDKeyPair.generate(KeyCurve.SECP256K1)
        assert len(kp.public_key_hex) == 130

    def test_secp256k1_private_key_length(self):
        """secp256k1 private key is 64 hex chars (32 bytes)."""
        kp = DIDKeyPair.generate(KeyCurve.SECP256K1)
        assert len(kp.private_key_hex) == 64

    def test_ed25519_public_key_length(self):
        """Ed25519 public key is 64 hex chars (32 bytes)."""
        kp = DIDKeyPair.generate(KeyCurve.ED25519)
        assert len(kp.public_key_hex) == 64

    def test_ed25519_private_key_length(self):
        """Ed25519 private key is 64 hex chars (32 bytes)."""
        kp = DIDKeyPair.generate(KeyCurve.ED25519)
        assert len(kp.private_key_hex) == 64

    def test_deterministic_secp256k1_same_seed(self):
        """Same seed → same secp256k1 key pair."""
        kp1 = DIDKeyPair.generate(KeyCurve.SECP256K1, seed="test-seed-42")
        kp2 = DIDKeyPair.generate(KeyCurve.SECP256K1, seed="test-seed-42")
        assert kp1.public_key_hex == kp2.public_key_hex
        assert kp1.private_key_hex == kp2.private_key_hex

    def test_deterministic_ed25519_same_seed(self):
        """Same seed → same ed25519 key pair."""
        kp1 = DIDKeyPair.generate(KeyCurve.ED25519, seed="ed-seed-1")
        kp2 = DIDKeyPair.generate(KeyCurve.ED25519, seed="ed-seed-1")
        assert kp1.public_key_hex == kp2.public_key_hex
        assert kp1.private_key_hex == kp2.private_key_hex

    def test_different_seeds_different_keys(self):
        """Different seeds → different keys."""
        kp1 = DIDKeyPair.generate(KeyCurve.SECP256K1, seed="alpha")
        kp2 = DIDKeyPair.generate(KeyCurve.SECP256K1, seed="beta")
        assert kp1.public_key_hex != kp2.public_key_hex
        assert kp1.private_key_hex != kp2.private_key_hex

    def test_random_generation_produces_valid_keys(self):
        """No seed → random but valid hex keys."""
        kp = DIDKeyPair.generate(KeyCurve.SECP256K1)
        # Should be valid hex
        bytes.fromhex(kp.public_key_hex)
        bytes.fromhex(kp.private_key_hex)
        # Two random generations should differ
        kp2 = DIDKeyPair.generate(KeyCurve.SECP256K1)
        assert kp.public_key_hex != kp2.public_key_hex

    def test_key_id_format(self):
        """Key ID is 'key-<8 hex chars>'."""
        kp = DIDKeyPair.generate(KeyCurve.SECP256K1, seed="id-test")
        assert kp.key_id.startswith("key-")
        assert len(kp.key_id) == 12  # "key-" + 8 hex chars
        # The 8 chars are SHA-1 of the public key hex
        expected_hash = hashlib.sha1(kp.public_key_hex.encode()).hexdigest()[:8]
        assert kp.key_id == f"key-{expected_hash}"

    def test_key_objects_present(self):
        """Generated key pair has actual cryptography key objects."""
        kp = DIDKeyPair.generate(KeyCurve.SECP256K1, seed="obj-test")
        assert kp._private_key_obj is not None
        assert kp._public_key_obj is not None
        assert isinstance(kp._private_key_obj, ec.EllipticCurvePrivateKey)
        assert isinstance(kp._public_key_obj, ec.EllipticCurvePublicKey)

    def test_reconstruct_key_objects_from_hex(self):
        """Setting _*_key_obj=None → __post_init__ reconstructs from hex."""
        kp_orig = DIDKeyPair.generate(KeyCurve.SECP256K1, seed="reconstruct")
        # Create a new DIDKeyPair with only hex, no key objects
        kp2 = DIDKeyPair(
            curve=KeyCurve.SECP256K1,
            public_key_hex=kp_orig.public_key_hex,
            private_key_hex=kp_orig.private_key_hex,
            key_id=kp_orig.key_id,
            # _private_key_obj and _public_key_obj default to None
        )
        assert kp2._private_key_obj is not None
        assert kp2._public_key_obj is not None
        # Signing with the reconstructed key produces a verifiable signature
        msg = b"test"
        sig = kp2._private_key_obj.sign(msg, ec.ECDSA(hashes.SHA256()))
        # Original public key can verify the reconstructed key's signature
        kp_orig._public_key_obj.verify(sig, msg, ec.ECDSA(hashes.SHA256()))
        # And vice-versa
        sig_orig = kp_orig._private_key_obj.sign(msg, ec.ECDSA(hashes.SHA256()))
        kp2._public_key_obj.verify(sig_orig, msg, ec.ECDSA(hashes.SHA256()))


# ═══════════════════════════════════════════════════════════════════════════
# 2. DID Creation (8 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestDIDCreation:
    """RingsDID.create_did() with both curves."""

    def test_secp256k1_did_format(self):
        """secp256k1 DID matches 'did:rings:secp256k1:<20 hex chars>'."""
        mgr = RingsDID()
        did, doc = mgr.create_did(curve=KeyCurve.SECP256K1, seed="fmt-test")
        assert did.startswith("did:rings:secp256k1:")
        fingerprint = did.split(":")[-1]
        assert len(fingerprint) == 20
        # Verify it's valid hex
        int(fingerprint, 16)

    def test_ed25519_did_format(self):
        """ed25519 DID matches 'did:rings:ed25519:<20 hex chars>'."""
        mgr = RingsDID(default_curve=KeyCurve.ED25519)
        did, doc = mgr.create_did(seed="ed-fmt")
        assert did.startswith("did:rings:ed25519:")
        fingerprint = did.split(":")[-1]
        assert len(fingerprint) == 20

    def test_verification_method_type_secp256k1(self):
        """secp256k1 DID doc has EcdsaSecp256k1VerificationKey2019."""
        mgr = RingsDID()
        did, doc = mgr.create_did(curve=KeyCurve.SECP256K1, seed="vm-type")
        vm = doc.verification_methods[0]
        assert vm["type"] == VerificationType.ECDSA_SECP256K1.value

    def test_verification_method_type_ed25519(self):
        """ed25519 DID doc has Ed25519VerificationKey2020."""
        mgr = RingsDID()
        did, doc = mgr.create_did(curve=KeyCurve.ED25519, seed="vm-ed")
        vm = doc.verification_methods[0]
        assert vm["type"] == VerificationType.ED25519.value

    def test_doc_public_key_matches_key_pair(self):
        """DID document publicKeyHex matches the generated key pair."""
        mgr = RingsDID()
        did, doc = mgr.create_did(seed="match-test")
        kp = mgr.get_key_pair(did)
        assert kp is not None
        assert doc.verification_methods[0]["publicKeyHex"] == kp.public_key_hex

    def test_multiple_dids_are_different(self):
        """Creating multiple DIDs produces unique values."""
        mgr = RingsDID()
        did1, _ = mgr.create_did(seed="multi-1")
        did2, _ = mgr.create_did(seed="multi-2")
        did3, _ = mgr.create_did()  # random
        assert did1 != did2
        assert did1 != did3
        assert did2 != did3

    def test_deterministic_did_from_seed(self):
        """Same seed → same DID across two managers."""
        mgr1 = RingsDID()
        mgr2 = RingsDID()
        did1, _ = mgr1.create_did(seed="det-did")
        did2, _ = mgr2.create_did(seed="det-did")
        assert did1 == did2

    def test_did_cached_after_creation(self):
        """Created DID is in local cache (resolve_local returns it)."""
        mgr = RingsDID()
        did, doc_orig = mgr.create_did(seed="cache-test")
        doc_resolved = mgr.resolve_local(did)
        assert doc_resolved is not None
        assert doc_resolved.did == did

    def test_document_serialization_roundtrip(self):
        """DIDDocument.to_dict() → DIDDocument.from_dict() preserves data."""
        mgr = RingsDID()
        did, doc = mgr.create_did(seed="roundtrip", services=[
            {"id": "svc-1", "type": "TestService", "serviceEndpoint": "http://example.com"},
        ])
        d = doc.to_dict()
        reconstructed = DIDDocument.from_dict(d)
        assert reconstructed.did == doc.did
        assert len(reconstructed.verification_methods) == len(doc.verification_methods)
        assert reconstructed.verification_methods[0]["publicKeyHex"] == doc.verification_methods[0]["publicKeyHex"]
        assert len(reconstructed.services) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 3. Proof Generation & Verification (15 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestProofGenAndVerify:
    """Real cryptographic proof sign/verify."""

    def test_secp256k1_sign_verify(self):
        """Create and verify a secp256k1 proof."""
        mgr = RingsDID()
        did, _ = mgr.create_did(curve=KeyCurve.SECP256K1, seed="proof-s256")
        proof = mgr.create_proof(did)
        assert mgr.verify_proof(did, proof)

    def test_ed25519_sign_verify(self):
        """Create and verify an ed25519 proof."""
        mgr = RingsDID()
        did, _ = mgr.create_did(curve=KeyCurve.ED25519, seed="proof-ed")
        proof = mgr.create_proof(did)
        assert mgr.verify_proof(did, proof)

    def test_proof_with_challenge(self):
        """Proof with a challenge string verifies correctly."""
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="challenge-test")
        proof = mgr.create_proof(did, challenge="nonce-abc-123")
        assert proof.challenge == "nonce-abc-123"
        assert mgr.verify_proof(did, proof)

    def test_proof_with_domain(self):
        """Proof with a domain string verifies correctly."""
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="domain-test")
        proof = mgr.create_proof(did, domain="example.com")
        assert proof.domain == "example.com"
        assert mgr.verify_proof(did, proof)

    def test_proof_with_challenge_and_domain(self):
        """Proof with both challenge and domain verifies."""
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="both-test")
        proof = mgr.create_proof(did, challenge="ch1", domain="dom1")
        assert mgr.verify_proof(did, proof)

    def test_wrong_challenge_fails(self):
        """Modifying the challenge in a proof makes verification fail."""
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="wrong-ch")
        proof = mgr.create_proof(did, challenge="original")
        # Tamper with the challenge
        proof.challenge = "tampered"
        assert not mgr.verify_proof(did, proof)

    def test_unknown_did_verify_fails(self):
        """Verifying proof for a DID not in local cache returns False."""
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="known")
        proof = mgr.create_proof(did)
        # Verify against a completely different DID string
        assert not mgr.verify_proof("did:rings:secp256k1:0000000000000000dead", proof)

    def test_tampered_signature_fails(self):
        """Flipping a byte in the signature hex makes verification fail."""
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="tamper-test")
        proof = mgr.create_proof(did)
        # Tamper with a byte in the middle of the signature
        sig_bytes = bytearray(bytes.fromhex(proof.signature))
        sig_bytes[len(sig_bytes) // 2] ^= 0xFF
        proof.signature = sig_bytes.hex()
        assert not mgr.verify_proof(did, proof)

    def test_cross_did_verification_fails(self):
        """Sign with DID A, attempt verify with DID B → failure."""
        mgr = RingsDID()
        did_a, _ = mgr.create_did(seed="alice")
        did_b, doc_b = mgr.create_did(seed="bob")
        proof_a = mgr.create_proof(did_a)
        # Try to verify A's proof as if it were B's
        assert not mgr.verify_proof(did_b, proof_a)

    def test_proof_signature_is_hex(self):
        """Proof signature is valid hexadecimal."""
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="hex-check")
        proof = mgr.create_proof(did)
        assert len(proof.signature) > 0
        bytes.fromhex(proof.signature)  # Should not raise

    def test_secp256k1_signature_is_der(self):
        """secp256k1 signature starts with 0x30 (DER SEQUENCE tag)."""
        mgr = RingsDID()
        did, _ = mgr.create_did(curve=KeyCurve.SECP256K1, seed="der-check")
        proof = mgr.create_proof(did)
        sig_bytes = bytes.fromhex(proof.signature)
        assert sig_bytes[0] == 0x30, f"Expected DER tag 0x30, got 0x{sig_bytes[0]:02x}"

    def test_ed25519_signature_length(self):
        """Ed25519 signature is 128 hex chars (64 bytes)."""
        mgr = RingsDID()
        did, _ = mgr.create_did(curve=KeyCurve.ED25519, seed="ed-sig-len")
        proof = mgr.create_proof(did)
        assert len(proof.signature) == 128

    def test_verify_using_public_key_hex_override(self):
        """Verify using public_key_hex parameter (simulates remote DID)."""
        mgr = RingsDID()
        did, doc = mgr.create_did(seed="remote-test")
        proof = mgr.create_proof(did)
        pubhex = doc.verification_methods[0]["publicKeyHex"]
        # Create a fresh manager that doesn't have the key pair cached
        mgr2 = RingsDID()
        # Verify using the explicit public key hex
        assert mgr2.verify_proof(did, proof, public_key_hex=pubhex)

    def test_proof_type_secp256k1(self):
        """secp256k1 proof type is 'EcdsaSecp256k1Signature2019'."""
        mgr = RingsDID()
        did, _ = mgr.create_did(curve=KeyCurve.SECP256K1, seed="pt-s")
        proof = mgr.create_proof(did)
        assert proof.proof_type == "EcdsaSecp256k1Signature2019"

    def test_proof_type_ed25519(self):
        """ed25519 proof type is 'Ed25519Signature2020'."""
        mgr = RingsDID()
        did, _ = mgr.create_did(curve=KeyCurve.ED25519, seed="pt-e")
        proof = mgr.create_proof(did)
        assert proof.proof_type == "Ed25519Signature2020"


# ═══════════════════════════════════════════════════════════════════════════
# 4. VID & Service (5 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestVIDAndService:
    """Virtual DID computation and service registration."""

    def test_compute_vid_deterministic(self):
        """Same inputs → same VID."""
        v1 = RingsDID.compute_vid("data", "my-dataset")
        v2 = RingsDID.compute_vid("data", "my-dataset")
        assert v1 == v2
        assert v1.startswith("vid:")

    def test_vid_to_position_in_range(self):
        """VID position is in [0, 2^160)."""
        vid = RingsDID.compute_vid("test", "key")
        pos = RingsDID.vid_to_position(vid)
        assert 0 <= pos < RING_MODULUS

    def test_add_service_to_did(self):
        """add_service appends a service entry to the DID document."""
        mgr = RingsDID()
        did, doc = mgr.create_did(seed="svc-test")
        assert len(doc.services) == 0
        mgr.add_service(did, "training", "ASIBuildTrainingNode", "http://localhost:8080")
        assert len(doc.services) == 1
        svc = doc.services[0]
        assert svc["id"] == f"{did}#svc-training"
        assert svc["type"] == "ASIBuildTrainingNode"
        assert svc["serviceEndpoint"] == "http://localhost:8080"

    def test_list_local_dids(self):
        """list_local_dids returns all created DIDs."""
        mgr = RingsDID()
        did1, _ = mgr.create_did(seed="list-1")
        did2, _ = mgr.create_did(seed="list-2")
        dids = mgr.list_local_dids()
        assert did1 in dids
        assert did2 in dids
        assert len(dids) >= 2

    def test_get_key_pair(self):
        """get_key_pair returns the correct key pair for a DID."""
        mgr = RingsDID()
        did, doc = mgr.create_did(seed="kp-get")
        kp = mgr.get_key_pair(did)
        assert kp is not None
        assert kp.public_key_hex == doc.verification_methods[0]["publicKeyHex"]
        assert kp.curve == KeyCurve.SECP256K1


# ═══════════════════════════════════════════════════════════════════════════
# 5. Edge Cases (5 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases and error paths."""

    def test_create_proof_nonexistent_did_raises(self):
        """create_proof for unknown DID raises ValueError."""
        mgr = RingsDID()
        with pytest.raises(ValueError, match="No local key"):
            mgr.create_proof("did:rings:secp256k1:nonexistent00000000")

    def test_verify_empty_signature_returns_false(self):
        """Verifying a proof with empty signature returns False."""
        mgr = RingsDID()
        did, _ = mgr.create_did(seed="empty-sig")
        proof = DIDProof(signature="")
        assert not mgr.verify_proof(did, proof)

    def test_resolve_local_works(self):
        """resolve_local returns the cached document."""
        mgr = RingsDID()
        did, doc_orig = mgr.create_did(seed="resolve-local")
        doc = mgr.resolve_local(did)
        assert doc is doc_orig

    def test_multiple_curves_same_manager(self):
        """A single manager can hold secp256k1 and ed25519 DIDs."""
        mgr = RingsDID()
        did_s, _ = mgr.create_did(curve=KeyCurve.SECP256K1, seed="multi-s")
        did_e, _ = mgr.create_did(curve=KeyCurve.ED25519, seed="multi-e")
        # Both work
        proof_s = mgr.create_proof(did_s)
        proof_e = mgr.create_proof(did_e)
        assert mgr.verify_proof(did_s, proof_s)
        assert mgr.verify_proof(did_e, proof_e)
        # Cross-verify fails
        assert not mgr.verify_proof(did_s, proof_e)
        assert not mgr.verify_proof(did_e, proof_s)

    def test_generate_with_none_seed_is_random(self):
        """DIDKeyPair.generate(seed=None) uses random key (not deterministic)."""
        kp1 = DIDKeyPair.generate(KeyCurve.SECP256K1, seed=None)
        kp2 = DIDKeyPair.generate(KeyCurve.SECP256K1, seed=None)
        # Astronomically unlikely to collide
        assert kp1.public_key_hex != kp2.public_key_hex
