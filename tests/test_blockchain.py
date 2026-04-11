"""
Tests for the blockchain module.

CRITICAL: All __init__.py files in the blockchain package are broken
(missing deps: eth_account, web3, ipfshttpclient, etc. and non-existent
submodules referenced in __init__.py). We bypass package imports entirely
and load individual .py files via importlib.util.

Testable pure-Python files:
  - crypto/hash_manager.py  (stdlib only, except optional Keccak)
  - web3_integration/network_config.py  (dataclasses + typing only)
"""

import importlib.util
import os
import sys
import json
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Module loader – bypasses broken __init__.py files
# ---------------------------------------------------------------------------
BASE = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    "src",
    "asi_build",
    "blockchain",
)
BASE = os.path.normpath(BASE)


def _load(name: str, relpath: str):
    """Load a single .py file as a standalone module."""
    full = os.path.join(BASE, relpath)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Attempt imports – skip gracefully if the file itself can't load
# ---------------------------------------------------------------------------
try:
    hash_mod = _load("hash_manager", "crypto/hash_manager.py")
    HashAlgorithm = hash_mod.HashAlgorithm
    HashResult = hash_mod.HashResult
    HashManager = hash_mod.HashManager
    MerkleTree = hash_mod.MerkleTree
    MerkleProof = hash_mod.MerkleProof
    MerkleNode = hash_mod.MerkleNode
    HashChain = hash_mod.HashChain
    HAS_HASH = True
except Exception as exc:
    HAS_HASH = False
    _hash_err = str(exc)

try:
    net_mod = _load("network_config", "web3_integration/network_config.py")
    NetworkConfig = net_mod.NetworkConfig
    NETWORKS = net_mod.NETWORKS
    NAMED_NETWORKS = net_mod.NAMED_NETWORKS
    get_network_by_chain_id = net_mod.get_network_by_chain_id
    get_network_by_name = net_mod.get_network_by_name
    get_testnet_networks = net_mod.get_testnet_networks
    get_mainnet_networks = net_mod.get_mainnet_networks
    get_l2_networks = net_mod.get_l2_networks
    validate_network_config = net_mod.validate_network_config
    get_network_summary = net_mod.get_network_summary
    # Named constants
    ETHEREUM_MAINNET = net_mod.ETHEREUM_MAINNET
    ETHEREUM_SEPOLIA = net_mod.ETHEREUM_SEPOLIA
    POLYGON_MAINNET = net_mod.POLYGON_MAINNET
    POLYGON_MUMBAI = net_mod.POLYGON_MUMBAI
    ARBITRUM_MAINNET = net_mod.ARBITRUM_MAINNET
    OPTIMISM_MAINNET = net_mod.OPTIMISM_MAINNET
    BSC_MAINNET = net_mod.BSC_MAINNET
    HAS_NET = True
except Exception as exc:
    HAS_NET = False
    _net_err = str(exc)


# ===================================================================
#  HashManager tests
# ===================================================================
@pytest.mark.skipif(not HAS_HASH, reason=f"hash_manager import failed: {_hash_err if not HAS_HASH else ''}")
class TestHashManager:
    """Tests for HashManager basic hashing operations."""

    def setup_method(self):
        self.hm = HashManager()

    # -- hash_data with different input types --

    def test_hash_string(self):
        result = self.hm.hash_data("hello world")
        assert isinstance(result, HashResult)
        assert result.algorithm == HashAlgorithm.SHA256
        assert len(result.hash_value) == 64  # SHA256 hex length
        assert result.input_size == len("hello world".encode())

    def test_hash_bytes(self):
        data = b"\x00\x01\x02\xff"
        result = self.hm.hash_data(data)
        assert result.input_size == 4
        assert len(result.hash_value) == 64

    def test_hash_dict_sorted(self):
        """Dicts are serialised with sort_keys=True so key order is irrelevant."""
        r1 = self.hm.hash_data({"b": 2, "a": 1})
        r2 = self.hm.hash_data({"a": 1, "b": 2})
        assert r1.hash_value == r2.hash_value

    def test_hash_list(self):
        result = self.hm.hash_data([1, 2, 3])
        assert isinstance(result, HashResult)

    # -- different algorithms --

    def test_hash_sha512(self):
        result = self.hm.hash_data("test", algorithm=HashAlgorithm.SHA512)
        assert result.algorithm == HashAlgorithm.SHA512
        assert len(result.hash_value) == 128  # SHA512 hex length

    def test_hash_sha3_256(self):
        result = self.hm.hash_data("test", algorithm=HashAlgorithm.SHA3_256)
        assert result.algorithm == HashAlgorithm.SHA3_256
        assert len(result.hash_value) == 64

    def test_hash_blake2b(self):
        result = self.hm.hash_data("test", algorithm=HashAlgorithm.BLAKE2B)
        assert result.algorithm == HashAlgorithm.BLAKE2B
        assert len(result.hash_value) == 128  # BLAKE2B default digest_size=64 → 128 hex

    def test_hash_blake2s(self):
        result = self.hm.hash_data("test", algorithm=HashAlgorithm.BLAKE2S)
        assert result.algorithm == HashAlgorithm.BLAKE2S
        assert len(result.hash_value) == 64  # BLAKE2S default digest_size=32 → 64 hex

    # -- verify_hash --

    def test_verify_hash_correct(self):
        result = self.hm.hash_data("hello")
        assert self.hm.verify_hash("hello", result.hash_value) is True

    def test_verify_hash_wrong(self):
        assert self.hm.verify_hash("hello", "0" * 64) is False

    # -- batch_hash --

    def test_batch_hash(self):
        items = ["alpha", "beta", "gamma"]
        results = self.hm.batch_hash(items)
        assert len(results) == 3
        assert all(isinstance(r, HashResult) for r in results)
        # All hashes must be unique
        hashes = [r.hash_value for r in results]
        assert len(set(hashes)) == 3

    # -- determinism --

    def test_deterministic(self):
        """Same data must always produce same hash."""
        r1 = self.hm.hash_data("deterministic")
        r2 = self.hm.hash_data("deterministic")
        assert r1.hash_value == r2.hash_value

    # -- metadata --

    def test_metadata_passed_through(self):
        meta = {"source": "test", "version": 1}
        result = self.hm.hash_data("data", metadata=meta)
        assert result.metadata == meta

    # -- hash_file --

    def test_hash_file(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
            f.write(b"file content for hashing")
            path = f.name
        try:
            result = self.hm.hash_file(path)
            assert isinstance(result, HashResult)
            assert result.input_size == len(b"file content for hashing")
        finally:
            os.unlink(path)

    # -- default algorithm override --

    def test_custom_default_algorithm(self):
        hm = HashManager(default_algorithm=HashAlgorithm.SHA512)
        result = hm.hash_data("test")
        assert result.algorithm == HashAlgorithm.SHA512


# ===================================================================
#  HashResult serialisation
# ===================================================================
@pytest.mark.skipif(not HAS_HASH, reason="hash_manager import failed")
class TestHashResultSerialization:

    def test_to_dict_and_back(self):
        hm = HashManager()
        original = hm.hash_data("round-trip")
        d = original.to_dict()
        restored = HashResult.from_dict(d)
        assert restored.hash_value == original.hash_value
        assert restored.algorithm == original.algorithm
        assert restored.input_size == original.input_size

    def test_to_dict_keys(self):
        hm = HashManager()
        d = hm.hash_data("keys").to_dict()
        assert set(d.keys()) == {"algorithm", "hash_value", "input_size", "timestamp", "metadata"}


# ===================================================================
#  MerkleTree tests
# ===================================================================
@pytest.mark.skipif(not HAS_HASH, reason="hash_manager import failed")
class TestMerkleTree:

    def _build(self, items):
        tree = MerkleTree()
        for item in items:
            tree.add_data(item)
        tree.build_tree()
        return tree

    def test_build_sets_root(self):
        tree = self._build(["a", "b"])
        assert tree.root is not None
        assert tree.get_root_hash() is not None

    def test_root_hash_is_string(self):
        tree = self._build(["x"])
        assert isinstance(tree.get_root_hash(), str)

    def test_two_leaves_proof_verifies(self):
        tree = self._build(["left", "right"])
        proof = tree.get_proof(0)
        assert tree.verify_proof(proof, "left") is True

    def test_two_leaves_second_proof_verifies(self):
        tree = self._build(["left", "right"])
        proof = tree.get_proof(1)
        assert tree.verify_proof(proof, "right") is True

    def test_four_leaves_all_proofs(self):
        data = ["a", "b", "c", "d"]
        tree = self._build(data)
        for i, item in enumerate(data):
            proof = tree.get_proof(i)
            assert tree.verify_proof(proof, item) is True, f"Proof failed for leaf {i}"

    def test_odd_leaves_handled(self):
        """Odd count → last node duplicated internally."""
        tree = self._build(["1", "2", "3"])
        assert tree.get_root_hash() is not None
        # All proofs should still verify
        for i, item in enumerate(["1", "2", "3"]):
            proof = tree.get_proof(i)
            assert tree.verify_proof(proof, item) is True

    def test_verify_wrong_data(self):
        tree = self._build(["real"])
        proof = tree.get_proof(0)
        assert tree.verify_proof(proof, "fake") is False

    def test_get_proof_invalid_index(self):
        tree = self._build(["a"])
        with pytest.raises(ValueError):
            tree.get_proof(5)

    def test_get_proof_before_build(self):
        tree = MerkleTree()
        tree.add_data("x")
        with pytest.raises(ValueError):
            tree.get_proof(0)

    def test_large_tree(self):
        data = [f"leaf_{i}" for i in range(8)]
        tree = self._build(data)
        for i, item in enumerate(data):
            proof = tree.get_proof(i)
            assert tree.verify_proof(proof, item) is True

    def test_root_deterministic(self):
        t1 = self._build(["a", "b", "c"])
        t2 = self._build(["a", "b", "c"])
        assert t1.get_root_hash() == t2.get_root_hash()

    def test_build_empty_raises(self):
        tree = MerkleTree()
        with pytest.raises(ValueError):
            tree.build_tree()


# ===================================================================
#  MerkleProof serialisation
# ===================================================================
@pytest.mark.skipif(not HAS_HASH, reason="hash_manager import failed")
class TestMerkleProofSerialization:

    def test_round_trip(self):
        tree = MerkleTree()
        tree.add_data("a")
        tree.add_data("b")
        tree.build_tree()
        proof = tree.get_proof(0)
        d = proof.to_dict()
        restored = MerkleProof.from_dict(d)
        assert restored.data_hash == proof.data_hash
        assert restored.root_hash == proof.root_hash
        assert restored.proof_hashes == proof.proof_hashes
        assert restored.proof_indices == proof.proof_indices


# ===================================================================
#  HashChain tests
# ===================================================================
@pytest.mark.skipif(not HAS_HASH, reason="hash_manager import failed")
class TestHashChain:

    def test_genesis_block_exists(self):
        chain = HashChain()
        assert len(chain.chain) == 1
        assert chain.chain[0]["index"] == 0

    def test_add_block_returns_hash(self):
        chain = HashChain()
        h = chain.add_block("block 1")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_chain_length_increases(self):
        chain = HashChain()
        chain.add_block("b1")
        chain.add_block("b2")
        assert len(chain.chain) == 3  # genesis + 2

    def test_get_chain_summary(self):
        chain = HashChain()
        summary = chain.get_chain_summary()
        assert summary["length"] == 1
        assert summary["algorithm"] == "sha256"
        assert "genesis_hash" in summary

    def test_export_chain_format(self):
        chain = HashChain()
        chain.add_block("data")
        exported = chain.export_chain()
        assert len(exported) == 2
        for block in exported:
            assert set(block.keys()) == {"index", "data", "hash", "previous_hash", "timestamp"}

    def test_custom_genesis_data(self):
        chain = HashChain(genesis_data="custom genesis")
        assert chain.chain[0]["data"] == "custom genesis"

    def test_sha512_algorithm(self):
        chain = HashChain(algorithm=HashAlgorithm.SHA512)
        assert len(chain.chain[0]["hash"]) == 128  # SHA512 hex

    def test_verify_genesis_only(self):
        """A chain with only the genesis block should verify (no blocks to re-hash)."""
        chain = HashChain()
        assert chain.verify_chain() is True

    def test_previous_hash_links(self):
        """Each block's previous_hash must equal the prior block's hash."""
        chain = HashChain()
        chain.add_block("x")
        chain.add_block("y")
        for i in range(1, len(chain.chain)):
            assert chain.chain[i]["previous_hash"] == chain.chain[i - 1]["hash"]

    # ----------------------------------------------------------------
    # KNOWN BUG: verify_chain() fails after add_block()
    # ----------------------------------------------------------------
    def test_verify_chain_timestamp_bug(self):
        """
        KNOWN BUG: add_block() calls datetime.now() TWICE —
          1) once when building block_data dict for hashing (line ~532),
          2) once when storing the block in self.chain (line ~543).
        verify_chain() recomputes the hash using the *stored* timestamp,
        which differs from the *hashed* timestamp.
        Result: verify_chain() always returns False for chains with >0 blocks.

        This test documents the bug so it doesn't surprise anyone.
        """
        chain = HashChain()
        chain.add_block("evidence of bug")
        # Because of the double datetime.now() call, verification fails:
        assert chain.verify_chain() is False, (
            "If this starts passing, the timestamp bug in add_block() may have been fixed!"
        )

    def test_verify_chain_works_with_frozen_time(self):
        """
        When time is frozen (same datetime.now() value for both calls in
        add_block), verify_chain() works correctly. This confirms the root
        cause is the double datetime.now() call.
        """
        frozen = datetime(2026, 1, 1, 12, 0, 0)
        chain = HashChain()
        with patch.object(hash_mod, "datetime") as mock_dt:
            mock_dt.now.return_value = frozen
            mock_dt.fromisoformat = datetime.fromisoformat
            # Need isoformat to work on the frozen datetime
            chain.add_block("frozen block")

        # The stored timestamp is now the same frozen datetime for both calls
        assert chain.verify_chain() is True


# ===================================================================
#  NetworkConfig tests
# ===================================================================
@pytest.mark.skipif(not HAS_NET, reason=f"network_config import failed: {_net_err if not HAS_NET else ''}")
class TestNetworkConfig:

    def test_ethereum_mainnet_chain_id(self):
        assert ETHEREUM_MAINNET.chain_id == 1

    def test_ethereum_sepolia_chain_id(self):
        assert ETHEREUM_SEPOLIA.chain_id == 11155111

    def test_polygon_mainnet_chain_id(self):
        assert POLYGON_MAINNET.chain_id == 137

    def test_all_11_networks_exist(self):
        assert len(NETWORKS) == 11

    def test_get_by_chain_id_found(self):
        net = get_network_by_chain_id(1)
        assert net is ETHEREUM_MAINNET

    def test_get_by_chain_id_missing(self):
        assert get_network_by_chain_id(999999) is None

    def test_get_by_name_ethereum(self):
        assert get_network_by_name("ethereum") is ETHEREUM_MAINNET

    def test_get_by_name_polygon(self):
        assert get_network_by_name("polygon") is POLYGON_MAINNET

    def test_get_by_name_case_insensitive(self):
        assert get_network_by_name("ETHEREUM") is ETHEREUM_MAINNET

    def test_get_by_name_nonexistent(self):
        assert get_network_by_name("nonexistent") is None

    def test_testnets(self):
        testnets = get_testnet_networks()
        assert all(n.is_testnet for n in testnets)
        assert len(testnets) >= 4  # goerli, sepolia, mumbai, arb-goerli, op-goerli, bsc-testnet

    def test_mainnets(self):
        mainnets = get_mainnet_networks()
        assert all(not n.is_testnet for n in mainnets)
        assert len(mainnets) >= 4  # eth, polygon, arb, op, bsc

    def test_l2_networks(self):
        l2s = get_l2_networks()
        l2_ids = {n.chain_id for n in l2s}
        # Should include Polygon, Arbitrum, Optimism (mainnet + testnet)
        assert 137 in l2_ids
        assert 42161 in l2_ids
        assert 10 in l2_ids

    def test_validate_valid_config(self):
        assert validate_network_config(ETHEREUM_MAINNET) is True

    def test_get_network_summary(self):
        summary = get_network_summary()
        assert isinstance(summary, dict)
        assert len(summary) == 11  # Same count as NETWORKS
        # Each entry should have expected keys
        for name, info in summary.items():
            assert "chain_id" in info
            assert "native_token" in info

    def test_network_config_fields(self):
        """Smoke-test that the dataclass fields are accessible."""
        cfg = ETHEREUM_MAINNET
        assert cfg.name == "Ethereum Mainnet"
        assert isinstance(cfg.rpc_urls, list)
        assert cfg.native_token == "ETH"
        assert cfg.supports_eip1559 is True
        assert cfg.confirmation_blocks == 12

    def test_arbitrum_is_l2(self):
        assert ARBITRUM_MAINNET.chain_id == 42161

    def test_bsc_no_eip1559(self):
        assert BSC_MAINNET.supports_eip1559 is False

    def test_validate_all_predefined(self):
        """Every predefined network should pass validation."""
        for chain_id, net in NETWORKS.items():
            assert validate_network_config(net) is True, f"Validation failed for chain {chain_id}"
