"""
Tests for RingsEthIdentity — unified Rings DID + Ethereum identity.

Covers: identity creation, Ethereum address derivation, Rings DID derivation,
EIP-191 signing, Rings protocol signing, EIP-712 typed data, and cross-identity
consistency checks.
"""

import hashlib
import os

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from asi_build.rings.eth_bridge import (
    RingsEthIdentity,
    SECP256K1_ORDER,
    _eip55_checksum,
    _keccak256,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Identity Creation (10 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentityCreation:
    """RingsEthIdentity constructors and basic properties."""

    def test_generate_creates_valid_identity(self):
        """generate() returns a RingsEthIdentity with all properties set."""
        identity = RingsEthIdentity.generate()
        assert identity.private_key_hex
        assert identity.public_key_hex
        assert identity.ethereum_address
        assert identity.rings_did

    def test_from_private_key_hex_valid(self):
        """from_private_key_hex() with valid 64-char hex works."""
        # Use a well-known private key (small value, valid for secp256k1)
        priv_hex = "0000000000000000000000000000000000000000000000000000000000000001"
        identity = RingsEthIdentity.from_private_key_hex(priv_hex)
        assert identity.private_key_hex == priv_hex

    def test_from_private_key_hex_with_0x_prefix(self):
        """from_private_key_hex() strips 0x prefix."""
        priv_hex = "0000000000000000000000000000000000000000000000000000000000000002"
        identity = RingsEthIdentity.from_private_key_hex("0x" + priv_hex)
        assert identity.private_key_hex == priv_hex

    def test_from_private_key_hex_invalid_length_raises(self):
        """from_private_key_hex() with wrong length raises ValueError."""
        with pytest.raises(ValueError, match="64 hex chars"):
            RingsEthIdentity.from_private_key_hex("abcd")

    def test_from_private_key_hex_zero_raises(self):
        """Private key = 0 is invalid for secp256k1."""
        zero_hex = "0" * 64
        with pytest.raises(ValueError, match="out of valid"):
            RingsEthIdentity.from_private_key_hex(zero_hex)

    def test_from_seed_deterministic(self):
        """from_seed() with same seed → same identity."""
        id1 = RingsEthIdentity.from_seed("test-alice")
        id2 = RingsEthIdentity.from_seed("test-alice")
        assert id1.private_key_hex == id2.private_key_hex
        assert id1.ethereum_address == id2.ethereum_address
        assert id1.rings_did == id2.rings_did

    def test_different_seeds_different_identities(self):
        """Different seeds → different identities."""
        id1 = RingsEthIdentity.from_seed("alice")
        id2 = RingsEthIdentity.from_seed("bob")
        assert id1.private_key_hex != id2.private_key_hex
        assert id1.ethereum_address != id2.ethereum_address

    def test_private_key_hex_is_64_chars(self):
        """Private key hex is exactly 64 characters."""
        identity = RingsEthIdentity.from_seed("len-check")
        assert len(identity.private_key_hex) == 64

    def test_public_key_hex_is_130_chars(self):
        """Uncompressed public key is 130 hex chars (04 + x + y)."""
        identity = RingsEthIdentity.from_seed("pub-len")
        assert len(identity.public_key_hex) == 130
        assert identity.public_key_hex[:2] == "04"

    def test_compressed_public_key_66_chars(self):
        """Compressed public key is 66 hex chars, starts with 02 or 03."""
        identity = RingsEthIdentity.from_seed("compressed-test")
        cpk = identity.public_key_compressed_hex
        assert len(cpk) == 66
        assert cpk[:2] in ("02", "03")

    def test_constructor_validates_curve(self):
        """Passing a non-secp256k1 key to constructor raises ValueError."""
        # Generate a P-256 key (not secp256k1)
        p256_key = ec.generate_private_key(ec.SECP256R1())
        with pytest.raises(ValueError, match="secp256k1"):
            RingsEthIdentity(p256_key)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Ethereum Address Derivation (10 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestEthereumAddress:
    """Ethereum address derivation and EIP-55 checksum."""

    def test_address_starts_with_0x(self):
        identity = RingsEthIdentity.from_seed("addr-0x")
        assert identity.ethereum_address.startswith("0x")

    def test_address_is_42_chars(self):
        """0x + 40 hex characters."""
        identity = RingsEthIdentity.from_seed("addr-42")
        assert len(identity.ethereum_address) == 42

    def test_address_is_eip55_checksummed(self):
        """Address matches EIP-55 checksum encoding."""
        identity = RingsEthIdentity.from_seed("addr-eip55")
        addr = identity.ethereum_address
        # Re-derive checksum from lowercase
        raw_hex = addr[2:].lower()
        expected = _eip55_checksum(raw_hex)
        assert addr == expected

    def test_same_key_same_address(self):
        """Same private key → same address."""
        id1 = RingsEthIdentity.from_seed("stable-addr")
        id2 = RingsEthIdentity.from_seed("stable-addr")
        assert id1.ethereum_address == id2.ethereum_address

    def test_known_test_vector(self):
        """Verify against a known private key → address mapping.

        Private key = 1 → known Ethereum address.
        (This is the generator point private key.)
        """
        priv_hex = "0000000000000000000000000000000000000000000000000000000000000001"
        identity = RingsEthIdentity.from_private_key_hex(priv_hex)
        # The Ethereum address for private key = 1 is well-known:
        # 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf
        expected = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        assert identity.ethereum_address.lower() == expected.lower()

    def test_address_derivation_uses_keccak256(self):
        """Address is keccak256(pubkey_xy)[-20:]."""
        identity = RingsEthIdentity.from_seed("keccak-check")
        pub_bytes = bytes.fromhex(identity.public_key_hex)
        pub_xy = pub_bytes[1:]  # strip 0x04 prefix
        full_hash = _keccak256(pub_xy)
        addr_bytes = full_hash[-20:]
        expected = _eip55_checksum(addr_bytes.hex())
        assert identity.ethereum_address == expected

    def test_different_keys_different_addresses(self):
        """Different keys → different addresses."""
        id1 = RingsEthIdentity.from_seed("diff-a")
        id2 = RingsEthIdentity.from_seed("diff-b")
        assert id1.ethereum_address != id2.ethereum_address

    def test_address_hex_chars_only(self):
        """Address after 0x contains only valid hex characters."""
        identity = RingsEthIdentity.from_seed("hex-only")
        hex_part = identity.ethereum_address[2:]
        assert all(c in "0123456789abcdefABCDEF" for c in hex_part)

    def test_private_key_2_address(self):
        """Private key = 2 → known address 0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF."""
        priv_hex = "0000000000000000000000000000000000000000000000000000000000000002"
        identity = RingsEthIdentity.from_private_key_hex(priv_hex)
        expected = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"
        assert identity.ethereum_address.lower() == expected.lower()

    def test_to_dict_contains_address(self):
        """to_dict() includes the ethereum_address."""
        identity = RingsEthIdentity.from_seed("dict-addr")
        d = identity.to_dict()
        assert d["ethereum_address"] == identity.ethereum_address
        assert d["rings_did"] == identity.rings_did
        assert d["public_key"] == identity.public_key_hex
        assert d["public_key_compressed"] == identity.public_key_compressed_hex


# ═══════════════════════════════════════════════════════════════════════════
# 3. Rings DID Derivation (5 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestRingsDIDDerivation:
    """Rings DID derivation from the same secp256k1 key."""

    def test_did_format(self):
        """DID is 'did:rings:secp256k1:<20 hex chars>'."""
        identity = RingsEthIdentity.from_seed("did-fmt")
        did = identity.rings_did
        assert did.startswith("did:rings:secp256k1:")
        fingerprint = did.split(":")[-1]
        assert len(fingerprint) == 20

    def test_same_key_same_did(self):
        """Deterministic: same key → same DID."""
        id1 = RingsEthIdentity.from_seed("stable-did")
        id2 = RingsEthIdentity.from_seed("stable-did")
        assert id1.rings_did == id2.rings_did

    def test_did_fingerprint_correct_length(self):
        """Fingerprint portion is 20 hex chars."""
        identity = RingsEthIdentity.from_seed("fp-len")
        fp = identity.rings_did.rsplit(":", 1)[-1]
        assert len(fp) == 20
        # Valid hex
        int(fp, 16)

    def test_different_keys_different_dids(self):
        """Different keys → different DIDs."""
        id1 = RingsEthIdentity.from_seed("did-a")
        id2 = RingsEthIdentity.from_seed("did-b")
        assert id1.rings_did != id2.rings_did

    def test_did_uses_compressed_pubkey_sha1(self):
        """Fingerprint = SHA1(compressed_pubkey_bytes)[:20]."""
        identity = RingsEthIdentity.from_seed("sha1-check")
        compressed = bytes.fromhex(identity.public_key_compressed_hex)
        expected_fp = hashlib.sha1(compressed).hexdigest()[:20]
        actual_fp = identity.rings_did.rsplit(":", 1)[-1]
        assert actual_fp == expected_fp


# ═══════════════════════════════════════════════════════════════════════════
# 4. EIP-191 Signing (10 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestEIP191Signing:
    """EIP-191 personal_sign signing and verification."""

    def test_sign_produces_65_bytes(self):
        """sign_ethereum returns 65 bytes (r + s + v)."""
        identity = RingsEthIdentity.from_seed("sig-len")
        sig = identity.sign_ethereum(b"Hello")
        assert len(sig) == 65

    def test_verify_valid_signature(self):
        """verify_ethereum returns True for a valid signature."""
        identity = RingsEthIdentity.from_seed("verify-ok")
        msg = b"Test message"
        sig = identity.sign_ethereum(msg)
        assert identity.verify_ethereum(msg, sig)

    def test_verify_wrong_message_fails(self):
        """verify_ethereum returns False for wrong message."""
        identity = RingsEthIdentity.from_seed("verify-fail")
        sig = identity.sign_ethereum(b"original")
        assert not identity.verify_ethereum(b"tampered", sig)

    def test_verify_tampered_signature_fails(self):
        """Flipping a byte in the signature → False."""
        identity = RingsEthIdentity.from_seed("tamper-sig")
        sig = bytearray(identity.sign_ethereum(b"message"))
        sig[10] ^= 0xFF
        assert not identity.verify_ethereum(b"message", bytes(sig))

    def test_sign_empty_message(self):
        """Signing an empty message works."""
        identity = RingsEthIdentity.from_seed("empty-msg")
        sig = identity.sign_ethereum(b"")
        assert len(sig) == 65
        assert identity.verify_ethereum(b"", sig)

    def test_sign_long_message(self):
        """Signing a large message works."""
        identity = RingsEthIdentity.from_seed("long-msg")
        msg = b"x" * 100_000
        sig = identity.sign_ethereum(msg)
        assert identity.verify_ethereum(msg, sig)

    def test_recover_address_matches(self):
        """Recovered address from signature matches identity's address."""
        identity = RingsEthIdentity.from_seed("recover-addr")
        msg = b"Recover me"
        sig = identity.sign_ethereum(msg)
        recovered = RingsEthIdentity.recover_ethereum_address(msg, sig)
        assert recovered.lower() == identity.ethereum_address.lower()

    def test_deterministic_signature_rfc6979(self):
        """ECDSA with eth_keys uses deterministic k: same msg+key → same sig."""
        identity = RingsEthIdentity.from_seed("det-sig")
        msg = b"deterministic test"
        sig1 = identity.sign_ethereum(msg)
        sig2 = identity.sign_ethereum(msg)
        assert sig1 == sig2

    def test_different_messages_different_signatures(self):
        """Different messages → different signatures."""
        identity = RingsEthIdentity.from_seed("diff-msg-sig")
        sig1 = identity.sign_ethereum(b"message A")
        sig2 = identity.sign_ethereum(b"message B")
        assert sig1 != sig2

    def test_v_byte_value(self):
        """The v byte (last byte) is 0 or 1 (pre-EIP-155)."""
        identity = RingsEthIdentity.from_seed("v-byte")
        sig = identity.sign_ethereum(b"check v")
        v = sig[-1]
        assert v in (0, 1), f"Expected v in (0,1), got {v}"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Rings Protocol Signing (8 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestRingsProtocolSigning:
    """ECDSA-SHA256 DER-encoded signing for Rings protocol."""

    def test_sign_returns_bytes(self):
        """sign_rings returns bytes."""
        identity = RingsEthIdentity.from_seed("rings-sig")
        sig = identity.sign_rings(b"Hello Rings")
        assert isinstance(sig, bytes)
        assert len(sig) > 0

    def test_verify_valid_signature(self):
        """verify_rings returns True for valid signature."""
        identity = RingsEthIdentity.from_seed("rings-verify")
        data = b"Test data"
        sig = identity.sign_rings(data)
        assert identity.verify_rings(data, sig)

    def test_verify_wrong_data_fails(self):
        """verify_rings returns False for wrong data."""
        identity = RingsEthIdentity.from_seed("rings-wrong")
        sig = identity.sign_rings(b"original data")
        assert not identity.verify_rings(b"different data", sig)

    def test_verify_wrong_signature_fails(self):
        """verify_rings returns False for wrong signature."""
        identity = RingsEthIdentity.from_seed("rings-bad-sig")
        sig = identity.sign_rings(b"data")
        bad_sig = b"\x00" * len(sig)
        assert not identity.verify_rings(b"data", bad_sig)

    def test_der_encoded_format(self):
        """Rings signature is DER-encoded (starts with 0x30 SEQUENCE tag)."""
        identity = RingsEthIdentity.from_seed("rings-der")
        sig = identity.sign_rings(b"DER check")
        assert sig[0] == 0x30, f"Expected 0x30, got 0x{sig[0]:02x}"

    def test_cross_identity_fails(self):
        """Sign with identity A, verify with identity B → False."""
        id_a = RingsEthIdentity.from_seed("rings-cross-a")
        id_b = RingsEthIdentity.from_seed("rings-cross-b")
        sig = id_a.sign_rings(b"cross check")
        assert not id_b.verify_rings(b"cross check", sig)

    def test_sign_empty_data(self):
        """Signing empty data works."""
        identity = RingsEthIdentity.from_seed("rings-empty")
        sig = identity.sign_rings(b"")
        assert identity.verify_rings(b"", sig)

    def test_sign_large_data(self):
        """Signing large data (1MB) works."""
        identity = RingsEthIdentity.from_seed("rings-large")
        data = os.urandom(1_000_000)
        sig = identity.sign_rings(data)
        assert identity.verify_rings(data, sig)


# ═══════════════════════════════════════════════════════════════════════════
# 6. EIP-712 Signing (8 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestEIP712Signing:
    """EIP-712 typed structured data signing."""

    _DOMAIN = {
        "name": "TestApp",
        "version": "1",
        "chainId": 1,
        "verifyingContract": "0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC",
    }
    _TYPES = {
        "Mail": [
            {"name": "from", "type": "string"},
            {"name": "to", "type": "string"},
            {"name": "contents", "type": "string"},
        ],
    }
    _MESSAGE = {
        "from": "Alice",
        "to": "Bob",
        "contents": "Hello Bob!",
    }

    def test_sign_produces_65_bytes(self):
        """sign_eip712 returns 65 bytes."""
        identity = RingsEthIdentity.from_seed("eip712-len")
        sig = identity.sign_eip712(self._DOMAIN, self._TYPES, self._MESSAGE)
        assert len(sig) == 65

    def test_verify_via_recovery(self):
        """Recovered address from EIP-712 sig matches identity."""
        identity = RingsEthIdentity.from_seed("eip712-verify")
        sig = identity.sign_eip712(self._DOMAIN, self._TYPES, self._MESSAGE)
        recovered = RingsEthIdentity.recover_eip712_address(
            self._DOMAIN, self._TYPES, self._MESSAGE, sig
        )
        assert recovered.lower() == identity.ethereum_address.lower()

    def test_different_domains_different_sigs(self):
        """Different domain → different signature."""
        identity = RingsEthIdentity.from_seed("eip712-dom")
        dom1 = {**self._DOMAIN, "name": "App1"}
        dom2 = {**self._DOMAIN, "name": "App2"}
        sig1 = identity.sign_eip712(dom1, self._TYPES, self._MESSAGE)
        sig2 = identity.sign_eip712(dom2, self._TYPES, self._MESSAGE)
        assert sig1 != sig2

    def test_different_messages_different_sigs(self):
        """Different message → different signature."""
        identity = RingsEthIdentity.from_seed("eip712-msg")
        msg1 = {**self._MESSAGE, "contents": "Hello A"}
        msg2 = {**self._MESSAGE, "contents": "Hello B"}
        sig1 = identity.sign_eip712(self._DOMAIN, self._TYPES, msg1)
        sig2 = identity.sign_eip712(self._DOMAIN, self._TYPES, msg2)
        assert sig1 != sig2

    def test_complex_nested_types(self):
        """EIP-712 with nested struct types signs and recovers correctly."""
        identity = RingsEthIdentity.from_seed("eip712-nested")
        types = {
            "Mail": [
                {"name": "from", "type": "Person"},
                {"name": "to", "type": "Person"},
                {"name": "contents", "type": "string"},
            ],
            "Person": [
                {"name": "name", "type": "string"},
                {"name": "wallet", "type": "address"},
            ],
        }
        message = {
            "from": {"name": "Alice", "wallet": "0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826"},
            "to": {"name": "Bob", "wallet": "0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB"},
            "contents": "Hello Bob!",
        }
        sig = identity.sign_eip712(self._DOMAIN, types, message, primary_type="Mail")
        assert len(sig) == 65
        recovered = RingsEthIdentity.recover_eip712_address(
            self._DOMAIN, types, message, sig, primary_type="Mail"
        )
        assert recovered.lower() == identity.ethereum_address.lower()

    def test_standard_domain_fields(self):
        """Full standard domain with name, version, chainId, verifyingContract."""
        identity = RingsEthIdentity.from_seed("eip712-std")
        domain = {
            "name": "My DApp",
            "version": "2",
            "chainId": 137,  # Polygon
            "verifyingContract": "0x1234567890abcdef1234567890abcdef12345678",
        }
        types = {
            "Action": [
                {"name": "user", "type": "address"},
                {"name": "amount", "type": "uint256"},
            ],
        }
        message = {
            "user": "0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826",
            "amount": 1000000,
        }
        sig = identity.sign_eip712(domain, types, message)
        assert len(sig) == 65
        recovered = RingsEthIdentity.recover_eip712_address(domain, types, message, sig)
        assert recovered.lower() == identity.ethereum_address.lower()

    def test_deterministic_eip712_signature(self):
        """Same domain + types + message + key → same signature (RFC 6979)."""
        identity = RingsEthIdentity.from_seed("eip712-det")
        sig1 = identity.sign_eip712(self._DOMAIN, self._TYPES, self._MESSAGE)
        sig2 = identity.sign_eip712(self._DOMAIN, self._TYPES, self._MESSAGE)
        assert sig1 == sig2

    def test_eip712_with_uint_and_bool_fields(self):
        """EIP-712 with uint256 and bool fields."""
        identity = RingsEthIdentity.from_seed("eip712-types")
        types = {
            "Order": [
                {"name": "amount", "type": "uint256"},
                {"name": "price", "type": "uint256"},
                {"name": "isBuy", "type": "bool"},
            ],
        }
        message = {"amount": 100, "price": 50, "isBuy": True}
        sig = identity.sign_eip712(self._DOMAIN, types, message)
        recovered = RingsEthIdentity.recover_eip712_address(
            self._DOMAIN, types, message, sig
        )
        assert recovered.lower() == identity.ethereum_address.lower()


# ═══════════════════════════════════════════════════════════════════════════
# 7. Cross-Identity Consistency (4 tests)
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossIdentityConsistency:
    """Consistency between Ethereum address, Rings DID, and crypto ops."""

    def test_same_key_same_address_and_did(self):
        """Same private key → same Ethereum address AND same Rings DID."""
        id1 = RingsEthIdentity.from_seed("cross-1")
        id2 = RingsEthIdentity.from_seed("cross-1")
        assert id1.ethereum_address == id2.ethereum_address
        assert id1.rings_did == id2.rings_did

    def test_eth_identity_rings_did_uses_compressed_key(self):
        """RingsEthIdentity.rings_did uses SHA1(compressed_pubkey_bytes).

        Note: RingsDID.create_did() uses SHA1(uncompressed_pubkey_hex.encode()),
        which is a different fingerprinting scheme.  This test documents the
        difference: RingsEthIdentity uses raw compressed bytes while
        RingsDID uses the ASCII hex of the uncompressed key.
        """
        identity = RingsEthIdentity.from_seed("cross-did-check")
        compressed_bytes = bytes.fromhex(identity.public_key_compressed_hex)
        expected_fp = hashlib.sha1(compressed_bytes).hexdigest()[:20]
        assert identity.rings_did == f"did:rings:secp256k1:{expected_fp}"

    def test_sign_rings_verify_works(self):
        """Sign with Rings method, verify succeeds."""
        identity = RingsEthIdentity.from_seed("cross-rings-sig")
        data = b"cross-identity rings signature"
        sig = identity.sign_rings(data)
        assert identity.verify_rings(data, sig)

    def test_sign_ethereum_recover_matches(self):
        """Sign with Ethereum method, recovered address matches."""
        identity = RingsEthIdentity.from_seed("cross-eth-sig")
        msg = b"cross-identity eth signature"
        sig = identity.sign_ethereum(msg)
        recovered = RingsEthIdentity.recover_ethereum_address(msg, sig)
        assert recovered.lower() == identity.ethereum_address.lower()

    def test_eq_and_hash(self):
        """Two identities from same seed are equal and hash-equal."""
        id1 = RingsEthIdentity.from_seed("eq-test")
        id2 = RingsEthIdentity.from_seed("eq-test")
        assert id1 == id2
        assert hash(id1) == hash(id2)

    def test_ne_different_seed(self):
        """Two identities from different seeds are not equal."""
        id1 = RingsEthIdentity.from_seed("ne-a")
        id2 = RingsEthIdentity.from_seed("ne-b")
        assert id1 != id2
