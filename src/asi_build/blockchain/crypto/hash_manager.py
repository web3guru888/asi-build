"""
Hash Management and Integrity Verification for Kenny AGI Blockchain Audit Trail

Provides comprehensive hashing functionality including Merkle trees,
hash chains, and integrity verification systems.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class HashAlgorithm(Enum):
    """Supported hash algorithms"""

    SHA256 = "sha256"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    KECCAK = "keccak"


@dataclass
class HashResult:
    """Result of a hash operation"""

    algorithm: HashAlgorithm
    hash_value: str
    input_size: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "algorithm": self.algorithm.value,
            "hash_value": self.hash_value,
            "input_size": self.input_size,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HashResult":
        """Create from dictionary"""
        return cls(
            algorithm=HashAlgorithm(data["algorithm"]),
            hash_value=data["hash_value"],
            input_size=data["input_size"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MerkleNode:
    """Node in a Merkle tree"""

    hash_value: str
    left_child: Optional["MerkleNode"] = None
    right_child: Optional["MerkleNode"] = None
    data: Optional[Any] = None
    index: Optional[int] = None

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node"""
        return self.left_child is None and self.right_child is None


@dataclass
class MerkleProof:
    """Merkle proof for data inclusion"""

    data_hash: str
    root_hash: str
    proof_hashes: List[str]
    proof_indices: List[int]  # 0 = left, 1 = right
    algorithm: HashAlgorithm

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "data_hash": self.data_hash,
            "root_hash": self.root_hash,
            "proof_hashes": self.proof_hashes,
            "proof_indices": self.proof_indices,
            "algorithm": self.algorithm.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MerkleProof":
        """Create from dictionary"""
        return cls(
            data_hash=data["data_hash"],
            root_hash=data["root_hash"],
            proof_hashes=data["proof_hashes"],
            proof_indices=data["proof_indices"],
            algorithm=HashAlgorithm(data["algorithm"]),
        )


class HashManager:
    """
    Comprehensive hash management system

    Provides various hashing algorithms and utilities for data integrity
    verification in the audit trail system.
    """

    def __init__(self, default_algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        """Initialize hash manager"""
        self.default_algorithm = default_algorithm

    def hash_data(
        self,
        data: Union[str, bytes, Dict, List],
        algorithm: Optional[HashAlgorithm] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HashResult:
        """
        Hash data using specified algorithm

        Args:
            data: Data to hash
            algorithm: Hash algorithm to use (default if None)
            metadata: Optional metadata

        Returns:
            Hash result
        """
        algorithm = algorithm or self.default_algorithm

        try:
            # Convert data to bytes
            if isinstance(data, str):
                data_bytes = data.encode("utf-8")
            elif isinstance(data, (dict, list)):
                data_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
            elif isinstance(data, bytes):
                data_bytes = data
            else:
                data_bytes = str(data).encode("utf-8")

            # Calculate hash based on algorithm
            if algorithm == HashAlgorithm.SHA256:
                hash_obj = hashlib.sha256(data_bytes)
            elif algorithm == HashAlgorithm.SHA512:
                hash_obj = hashlib.sha512(data_bytes)
            elif algorithm == HashAlgorithm.SHA3_256:
                hash_obj = hashlib.sha3_256(data_bytes)
            elif algorithm == HashAlgorithm.SHA3_512:
                hash_obj = hashlib.sha3_512(data_bytes)
            elif algorithm == HashAlgorithm.BLAKE2B:
                hash_obj = hashlib.blake2b(data_bytes)
            elif algorithm == HashAlgorithm.BLAKE2S:
                hash_obj = hashlib.blake2s(data_bytes)
            elif algorithm == HashAlgorithm.KECCAK:
                # Using Keccak-256 (Ethereum standard)
                import Crypto.Hash.keccak

                hash_obj = Crypto.Hash.keccak.new(digest_bits=256)
                hash_obj.update(data_bytes)
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")

            hash_value = hash_obj.hexdigest()

            result = HashResult(
                algorithm=algorithm,
                hash_value=hash_value,
                input_size=len(data_bytes),
                timestamp=datetime.now(),
                metadata=metadata or {},
            )

            logger.debug(f"Hashed data using {algorithm.value}: {hash_value[:16]}...")
            return result

        except Exception as e:
            raise RuntimeError(f"Failed to hash data: {str(e)}")

    def hash_file(
        self,
        file_path: str,
        algorithm: Optional[HashAlgorithm] = None,
        chunk_size: int = 8192,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HashResult:
        """
        Hash a file using specified algorithm

        Args:
            file_path: Path to file to hash
            algorithm: Hash algorithm to use
            chunk_size: Size of chunks to read
            metadata: Optional metadata

        Returns:
            Hash result
        """
        algorithm = algorithm or self.default_algorithm

        try:
            # Initialize hash object
            if algorithm == HashAlgorithm.SHA256:
                hash_obj = hashlib.sha256()
            elif algorithm == HashAlgorithm.SHA512:
                hash_obj = hashlib.sha512()
            elif algorithm == HashAlgorithm.SHA3_256:
                hash_obj = hashlib.sha3_256()
            elif algorithm == HashAlgorithm.SHA3_512:
                hash_obj = hashlib.sha3_512()
            elif algorithm == HashAlgorithm.BLAKE2B:
                hash_obj = hashlib.blake2b()
            elif algorithm == HashAlgorithm.BLAKE2S:
                hash_obj = hashlib.blake2s()
            elif algorithm == HashAlgorithm.KECCAK:
                import Crypto.Hash.keccak

                hash_obj = Crypto.Hash.keccak.new(digest_bits=256)
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")

            # Read file in chunks and update hash
            total_size = 0
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hash_obj.update(chunk)
                    total_size += len(chunk)

            hash_value = hash_obj.hexdigest()

            result = HashResult(
                algorithm=algorithm,
                hash_value=hash_value,
                input_size=total_size,
                timestamp=datetime.now(),
                metadata=metadata or {},
            )

            logger.info(f"Hashed file {file_path} using {algorithm.value}: {hash_value[:16]}...")
            return result

        except Exception as e:
            raise RuntimeError(f"Failed to hash file {file_path}: {str(e)}")

    def verify_hash(
        self,
        data: Union[str, bytes, Dict, List],
        expected_hash: str,
        algorithm: Optional[HashAlgorithm] = None,
    ) -> bool:
        """
        Verify data against expected hash

        Args:
            data: Data to verify
            expected_hash: Expected hash value
            algorithm: Hash algorithm used

        Returns:
            True if hash matches
        """
        try:
            hash_result = self.hash_data(data, algorithm)
            return hash_result.hash_value == expected_hash
        except Exception as e:
            logger.error(f"Hash verification failed: {str(e)}")
            return False

    def batch_hash(
        self,
        data_list: List[Union[str, bytes, Dict, List]],
        algorithm: Optional[HashAlgorithm] = None,
    ) -> List[HashResult]:
        """
        Hash multiple pieces of data in batch

        Args:
            data_list: List of data to hash
            algorithm: Hash algorithm to use

        Returns:
            List of hash results
        """
        results = []

        for data in data_list:
            try:
                result = self.hash_data(data, algorithm)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to hash data item: {str(e)}")
                results.append(None)

        return results


class MerkleTree:
    """
    Merkle Tree implementation for data integrity verification

    Provides efficient verification of data inclusion and integrity
    for large datasets in the audit trail.
    """

    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        """Initialize Merkle tree"""
        self.algorithm = algorithm
        self.root = None
        self.leaves = []
        self.hash_manager = HashManager(algorithm)

    def add_data(self, data: Union[str, bytes, Dict, List]):
        """Add data to the tree"""
        hash_result = self.hash_manager.hash_data(data)
        leaf = MerkleNode(hash_value=hash_result.hash_value, data=data, index=len(self.leaves))
        self.leaves.append(leaf)

    def build_tree(self):
        """Build the Merkle tree from current leaves"""
        if not self.leaves:
            raise ValueError("No data to build tree from")

        # Start with leaves
        current_level = self.leaves.copy()

        # Build tree bottom-up
        while len(current_level) > 1:
            next_level = []

            # Pair up nodes
            for i in range(0, len(current_level), 2):
                left = current_level[i]

                # If odd number of nodes, duplicate the last one
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left

                # Create parent node
                combined_hash = left.hash_value + right.hash_value
                parent_hash = self.hash_manager.hash_data(combined_hash)

                parent = MerkleNode(
                    hash_value=parent_hash.hash_value, left_child=left, right_child=right
                )

                next_level.append(parent)

            current_level = next_level

        self.root = current_level[0]
        logger.info(f"Built Merkle tree with root: {self.root.hash_value[:16]}...")

    def get_root_hash(self) -> Optional[str]:
        """Get root hash of the tree"""
        return self.root.hash_value if self.root else None

    def get_proof(self, data_index: int) -> MerkleProof:
        """
        Generate Merkle proof for data at given index

        Args:
            data_index: Index of data in leaves array

        Returns:
            Merkle proof for the data
        """
        if not self.root:
            raise ValueError("Tree not built yet")

        if data_index >= len(self.leaves):
            raise ValueError("Data index out of range")

        leaf = self.leaves[data_index]
        proof_hashes = []
        proof_indices = []

        # Traverse from leaf to root
        current = leaf
        current_index = data_index

        # Find path to root
        nodes_at_level = self.leaves.copy()

        while len(nodes_at_level) > 1:
            # Find sibling
            if current_index % 2 == 0:  # Left child
                sibling_index = current_index + 1
                if sibling_index < len(nodes_at_level):
                    sibling = nodes_at_level[sibling_index]
                    proof_hashes.append(sibling.hash_value)
                    proof_indices.append(1)  # Sibling is on the right
                else:
                    # Duplicate current node as sibling
                    proof_hashes.append(current.hash_value)
                    proof_indices.append(1)
            else:  # Right child
                sibling_index = current_index - 1
                sibling = nodes_at_level[sibling_index]
                proof_hashes.append(sibling.hash_value)
                proof_indices.append(0)  # Sibling is on the left

            # Move to next level
            next_level = []
            for i in range(0, len(nodes_at_level), 2):
                left = nodes_at_level[i]
                right = nodes_at_level[i + 1] if i + 1 < len(nodes_at_level) else left

                combined_hash = left.hash_value + right.hash_value
                parent_hash = self.hash_manager.hash_data(combined_hash)

                parent = MerkleNode(hash_value=parent_hash.hash_value)
                next_level.append(parent)

            nodes_at_level = next_level
            current_index = current_index // 2

        return MerkleProof(
            data_hash=leaf.hash_value,
            root_hash=self.root.hash_value,
            proof_hashes=proof_hashes,
            proof_indices=proof_indices,
            algorithm=self.algorithm,
        )

    def verify_proof(self, proof: MerkleProof, data: Union[str, bytes, Dict, List]) -> bool:
        """
        Verify Merkle proof for given data

        Args:
            proof: Merkle proof to verify
            data: Original data

        Returns:
            True if proof is valid
        """
        try:
            # Hash the data
            data_hash_result = self.hash_manager.hash_data(data)

            if data_hash_result.hash_value != proof.data_hash:
                return False

            # Reconstruct root hash using proof
            current_hash = proof.data_hash

            for i, (proof_hash, direction) in enumerate(
                zip(proof.proof_hashes, proof.proof_indices)
            ):
                if direction == 0:  # Proof hash is on the left
                    combined = proof_hash + current_hash
                else:  # Proof hash is on the right
                    combined = current_hash + proof_hash

                hash_result = self.hash_manager.hash_data(combined)
                current_hash = hash_result.hash_value

            return current_hash == proof.root_hash

        except Exception as e:
            logger.error(f"Merkle proof verification failed: {str(e)}")
            return False


class HashChain:
    """
    Hash Chain implementation for sequential integrity verification

    Creates a chain of hashes where each hash depends on the previous one,
    providing tamper-evident sequencing for audit records.
    """

    def __init__(
        self, algorithm: HashAlgorithm = HashAlgorithm.SHA256, genesis_data: Optional[str] = None
    ):
        """Initialize hash chain"""
        self.algorithm = algorithm
        self.hash_manager = HashManager(algorithm)
        self.chain = []

        # Create genesis block
        genesis_data = genesis_data or "Genesis Block"
        genesis_hash = self.hash_manager.hash_data(genesis_data)

        self.chain.append(
            {
                "index": 0,
                "data": genesis_data,
                "hash": genesis_hash.hash_value,
                "previous_hash": "0" * 64,
                "timestamp": datetime.now(),
            }
        )

        logger.info(f"Initialized hash chain with genesis hash: {genesis_hash.hash_value[:16]}...")

    def add_block(self, data: Union[str, bytes, Dict, List]) -> str:
        """
        Add new block to the chain

        Args:
            data: Data to add to the chain

        Returns:
            Hash of the new block
        """
        previous_block = self.chain[-1]
        index = len(self.chain)

        # Create block data including previous hash
        block_data = {
            "index": index,
            "data": data,
            "previous_hash": previous_block["hash"],
            "timestamp": datetime.now().isoformat(),
        }

        # Hash the entire block
        block_hash = self.hash_manager.hash_data(block_data)

        # Add to chain
        block = {
            "index": index,
            "data": data,
            "hash": block_hash.hash_value,
            "previous_hash": previous_block["hash"],
            "timestamp": datetime.now(),
        }

        self.chain.append(block)

        logger.info(f"Added block {index} to hash chain: {block_hash.hash_value[:16]}...")
        return block_hash.hash_value

    def verify_chain(self) -> bool:
        """
        Verify integrity of the entire hash chain

        Returns:
            True if chain is valid
        """
        try:
            for i in range(1, len(self.chain)):
                current_block = self.chain[i]
                previous_block = self.chain[i - 1]

                # Check if previous hash matches
                if current_block["previous_hash"] != previous_block["hash"]:
                    logger.error(f"Hash chain broken at block {i}: previous hash mismatch")
                    return False

                # Verify current block hash
                block_data = {
                    "index": current_block["index"],
                    "data": current_block["data"],
                    "previous_hash": current_block["previous_hash"],
                    "timestamp": current_block["timestamp"].isoformat(),
                }

                expected_hash = self.hash_manager.hash_data(block_data)

                if expected_hash.hash_value != current_block["hash"]:
                    logger.error(f"Hash chain broken at block {i}: block hash mismatch")
                    return False

            logger.info("Hash chain verification successful")
            return True

        except Exception as e:
            logger.error(f"Hash chain verification failed: {str(e)}")
            return False

    def get_chain_summary(self) -> Dict[str, Any]:
        """Get summary of the hash chain"""
        return {
            "length": len(self.chain),
            "algorithm": self.algorithm.value,
            "genesis_hash": self.chain[0]["hash"],
            "latest_hash": self.chain[-1]["hash"],
            "created_at": self.chain[0]["timestamp"].isoformat(),
            "last_updated": self.chain[-1]["timestamp"].isoformat(),
        }

    def export_chain(self) -> List[Dict[str, Any]]:
        """Export the entire hash chain"""
        return [
            {
                "index": block["index"],
                "data": block["data"],
                "hash": block["hash"],
                "previous_hash": block["previous_hash"],
                "timestamp": block["timestamp"].isoformat(),
            }
            for block in self.chain
        ]
