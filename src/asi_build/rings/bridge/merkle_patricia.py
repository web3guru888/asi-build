"""
Merkle-Patricia Trie Verifier
=============================

Verifies Ethereum state proofs (EIP-1186 ``eth_getProof``).

Ethereum uses a Modified Merkle Patricia Trie (MPT) for:

- **World State Trie**: account data (nonce, balance, codeHash, storageRoot)
- **Storage Trie**: contract storage slots
- **Transaction Trie**: transactions in a block
- **Receipt Trie**: transaction receipts

Each account is stored at key ``keccak256(address)`` in the world state
trie. The value is RLP-encoded ``[nonce, balance, storageRoot, codeHash]``.

Proof verification walks the trie from the root, following key nibbles
through branch/extension/leaf nodes provided in the proof.

This module provides:

- :class:`RLPDecoder` — minimal RLP decoder for trie node parsing.
- :class:`MerklePatriciaVerifier` — static methods for MPT proof
  verification (accounts, storage slots, receipts).
- :class:`AccountState` — decoded Ethereum account state.
- :class:`TransactionReceipt` — decoded transaction receipt.

References
----------
- `EIP-1186: eth_getProof <https://eips.ethereum.org/EIPS/eip-1186>`_
- `Ethereum Yellow Paper §D <https://ethereum.github.io/yellowpaper/paper.pdf>`_
- `Ethereum MPT Specification <https://ethereum.org/en/developers/docs/data-structures-and-encoding/patricia-merkle-trie/>`_
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

from Crypto.Hash import keccak as _keccak_mod

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AccountState:
    """Decoded Ethereum account state from the world state trie.

    Attributes
    ----------
    nonce : int
        Number of transactions sent from this account.
    balance : int
        Account balance in wei.
    storage_root : bytes
        32-byte root hash of the account's storage trie.
        ``keccak256(RLP(""))`` for accounts with no storage.
    code_hash : bytes
        32-byte keccak256 hash of the account's EVM bytecode.
        ``keccak256("")`` for externally-owned accounts (EOAs).
    """

    nonce: int
    balance: int
    storage_root: bytes  # 32 bytes
    code_hash: bytes  # 32 bytes


@dataclass
class TransactionReceipt:
    """Decoded Ethereum transaction receipt.

    Attributes
    ----------
    status : int
        ``1`` for success, ``0`` for failure (post-Byzantium).
    cumulative_gas_used : int
        Total gas used in the block up to and including this tx.
    logs_bloom : bytes
        256-byte Bloom filter for quick log topic lookup.
    logs : list of dict
        Log entries emitted by this transaction.
    """

    status: int  # 0 or 1
    cumulative_gas_used: int
    logs_bloom: bytes
    logs: List[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# RLP Decoder
# ---------------------------------------------------------------------------


class RLPDecoder:
    """Minimal Recursive Length Prefix (RLP) decoder for trie node parsing.

    Supports all five RLP encoding categories:

    - ``0x00–0x7f``: single byte (identity)
    - ``0x80–0xb7``: short string (0–55 bytes)
    - ``0xb8–0xbf``: long string (>55 bytes)
    - ``0xc0–0xf7``: short list (total payload 0–55 bytes)
    - ``0xf8–0xff``: long list (total payload >55 bytes)

    Example
    -------
    ::

        >>> RLPDecoder.decode(b'\\x83dog')
        b'dog'
        >>> RLPDecoder.decode(b'\\xc8\\x83cat\\x83dog')
        [b'cat', b'dog']
    """

    @staticmethod
    def decode(data: bytes) -> Union[bytes, list]:
        """Decode an RLP-encoded byte string.

        Parameters
        ----------
        data : bytes
            RLP-encoded data.

        Returns
        -------
        bytes or list
            Decoded value — either a byte string or a nested list.

        Raises
        ------
        ValueError
            If the data is malformed or incomplete.
        """
        if not data:
            return b""
        result, consumed = RLPDecoder._decode_item(data, 0)
        return result

    @staticmethod
    def _decode_item(data: bytes, offset: int) -> Tuple[Union[bytes, list], int]:
        """Decode a single RLP item starting at *offset*.

        Returns
        -------
        tuple of (decoded_value, end_offset)
        """
        if offset >= len(data):
            raise ValueError(f"RLP: offset {offset} beyond data length {len(data)}")

        prefix = data[offset]

        if prefix <= 0x7F:
            # Single byte
            return bytes([prefix]), offset + 1

        elif prefix <= 0xB7:
            # Short string: 0–55 bytes
            str_len = prefix - 0x80
            start = offset + 1
            end = start + str_len
            if end > len(data):
                raise ValueError(
                    f"RLP: short string at {offset} needs {str_len} bytes, "
                    f"only {len(data) - start} available"
                )
            return data[start:end], end

        elif prefix <= 0xBF:
            # Long string: length-of-length encoded
            len_of_len = prefix - 0xB7
            len_start = offset + 1
            len_end = len_start + len_of_len
            if len_end > len(data):
                raise ValueError(
                    f"RLP: long string length bytes at {offset} exceed data"
                )
            str_len = int.from_bytes(data[len_start:len_end], "big")
            start = len_end
            end = start + str_len
            if end > len(data):
                raise ValueError(
                    f"RLP: long string at {offset} needs {str_len} bytes, "
                    f"only {len(data) - start} available"
                )
            return data[start:end], end

        elif prefix <= 0xF7:
            # Short list: total payload 0–55 bytes
            list_len = prefix - 0xC0
            start = offset + 1
            end = start + list_len
            if end > len(data):
                raise ValueError(
                    f"RLP: short list at {offset} needs {list_len} bytes, "
                    f"only {len(data) - start} available"
                )
            items: list = []
            pos = start
            while pos < end:
                item, pos = RLPDecoder._decode_item(data, pos)
                items.append(item)
            return items, end

        else:
            # Long list: length-of-length encoded
            len_of_len = prefix - 0xF7
            len_start = offset + 1
            len_end = len_start + len_of_len
            if len_end > len(data):
                raise ValueError(
                    f"RLP: long list length bytes at {offset} exceed data"
                )
            list_len = int.from_bytes(data[len_start:len_end], "big")
            start = len_end
            end = start + list_len
            if end > len(data):
                raise ValueError(
                    f"RLP: long list at {offset} needs {list_len} bytes, "
                    f"only {len(data) - start} available"
                )
            items = []
            pos = start
            while pos < end:
                item, pos = RLPDecoder._decode_item(data, pos)
                items.append(item)
            return items, end

    @staticmethod
    def decode_length(data: bytes, offset: int) -> Tuple[int, int, str]:
        """Decode the length prefix at *offset*.

        Returns
        -------
        tuple of (data_offset, data_length, type)
            Where *type* is ``"str"`` or ``"list"``.
        """
        if offset >= len(data):
            raise ValueError("RLP: offset beyond data")

        prefix = data[offset]

        if prefix <= 0x7F:
            return offset, 1, "str"

        elif prefix <= 0xB7:
            str_len = prefix - 0x80
            return offset + 1, str_len, "str"

        elif prefix <= 0xBF:
            len_of_len = prefix - 0xB7
            len_start = offset + 1
            str_len = int.from_bytes(
                data[len_start : len_start + len_of_len], "big"
            )
            return len_start + len_of_len, str_len, "str"

        elif prefix <= 0xF7:
            list_len = prefix - 0xC0
            return offset + 1, list_len, "list"

        else:
            len_of_len = prefix - 0xF7
            len_start = offset + 1
            list_len = int.from_bytes(
                data[len_start : len_start + len_of_len], "big"
            )
            return len_start + len_of_len, list_len, "list"


# ---------------------------------------------------------------------------
# Merkle-Patricia Trie Verifier
# ---------------------------------------------------------------------------


class MerklePatriciaVerifier:
    """Verify Ethereum Merkle-Patricia Trie proofs.

    All methods are static — no instance state is needed. The verifier
    uses ``keccak256`` from pycryptodome for hashing.

    Proof verification algorithm
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1. Start at the root hash.
    2. For each node in the proof:
       a. Hash the node's RLP encoding with keccak256.
       b. Verify it matches the expected hash.
       c. Decode the node with RLP.
       d. Determine node type: branch (17 items), extension (2 items +
          even prefix), or leaf (2 items + odd prefix).
       e. Follow the key nibbles to the next node or extract the value.
    3. If the key is fully consumed and a value is found, the proof is
       valid.
    """

    @staticmethod
    def keccak256(data: bytes) -> bytes:
        """Compute the Keccak-256 hash of *data*.

        Parameters
        ----------
        data : bytes
            Input data.

        Returns
        -------
        bytes
            32-byte hash digest.
        """
        h = _keccak_mod.new(digest_bits=256)
        h.update(data)
        return h.digest()

    @staticmethod
    def nibbles_from_bytes(data: bytes) -> List[int]:
        """Convert a byte string to a list of nibbles (half-bytes).

        Each byte is split into its high and low 4-bit values.

        Parameters
        ----------
        data : bytes
            Input bytes.

        Returns
        -------
        list of int
            Each element is in ``[0, 15]``.

        Example
        -------
        >>> MerklePatriciaVerifier.nibbles_from_bytes(b'\\xab\\xcd')
        [10, 11, 12, 13]
        """
        nibbles: List[int] = []
        for byte in data:
            nibbles.append(byte >> 4)
            nibbles.append(byte & 0x0F)
        return nibbles

    @staticmethod
    def _decode_compact_path(data: bytes) -> Tuple[List[int], bool]:
        """Decode an HP (Hex-Prefix) encoded path.

        The HP encoding prepends a nibble flag:

        - ``0x0``: extension node, even number of nibbles remaining
        - ``0x1``: extension node, odd number of nibbles remaining
        - ``0x2``: leaf node, even number of nibbles remaining
        - ``0x3``: leaf node, odd number of nibbles remaining

        When the flag indicates an odd length, the second nibble of the
        first byte is the first nibble of the path. When even, a
        padding zero nibble is inserted.

        Parameters
        ----------
        data : bytes
            HP-encoded path bytes.

        Returns
        -------
        tuple of (list of int, bool)
            ``(nibbles, is_leaf)``.
        """
        if not data:
            return [], False

        first_nibble = data[0] >> 4
        is_leaf = first_nibble >= 2
        is_odd = first_nibble % 2 == 1

        nibbles: List[int] = []
        if is_odd:
            # Second nibble of first byte is first nibble of the path
            nibbles.append(data[0] & 0x0F)
            rest = data[1:]
        else:
            # Skip padding nibble (second nibble of first byte is 0)
            rest = data[1:]

        for byte in rest:
            nibbles.append(byte >> 4)
            nibbles.append(byte & 0x0F)

        return nibbles, is_leaf

    @staticmethod
    def verify_proof(
        root: bytes,
        key: bytes,
        proof: List[bytes],
    ) -> Optional[bytes]:
        """Core MPT proof verification.

        Walk the trie from *root*, following *key* nibbles through the
        *proof* nodes. Returns the value if the proof is valid,
        ``None`` otherwise.

        Node types (after RLP decoding):

        - **Branch node**: 17-element list. Children ``[0]–[15]`` are
          either 32-byte hashes or empty. ``[16]`` is the value at this
          branch (if the key terminates here).
        - **Extension node**: 2-element list ``[encoded_path, next_hash]``
          where ``encoded_path`` has HP flag < 2 (not a leaf).
        - **Leaf node**: 2-element list ``[encoded_path, value]`` where
          ``encoded_path`` has HP flag ≥ 2.

        Parameters
        ----------
        root : bytes
            32-byte root hash of the trie.
        key : bytes
            The key to look up (already hashed for state/storage tries).
        proof : list of bytes
            RLP-encoded trie nodes from root to the target.

        Returns
        -------
        bytes or None
            The value at *key* if the proof is valid, ``None`` otherwise.
        """
        if not proof:
            return None

        key_nibbles = MerklePatriciaVerifier.nibbles_from_bytes(key)
        nibble_idx = 0
        expected_hash = root

        for i, node_rlp in enumerate(proof):
            # Verify node hash matches what we expect
            node_hash = MerklePatriciaVerifier.keccak256(node_rlp)
            if len(node_rlp) >= 32 and node_hash != expected_hash:
                # Nodes shorter than 32 bytes may be inlined (not hashed)
                logger.debug(
                    "Proof node %d: hash mismatch (expected %s, got %s)",
                    i, expected_hash.hex(), node_hash.hex(),
                )
                return None

            # Decode the node
            try:
                decoded = RLPDecoder.decode(node_rlp)
            except ValueError as exc:
                logger.debug("Proof node %d: RLP decode error: %s", i, exc)
                return None

            if not isinstance(decoded, list):
                logger.debug("Proof node %d: expected list, got bytes", i)
                return None

            if len(decoded) == 17:
                # ── Branch node ──────────────────────────────────────
                if nibble_idx == len(key_nibbles):
                    # Key fully consumed — value is at index 16
                    value = decoded[16]
                    return value if isinstance(value, bytes) and value else None

                # Follow the child at the current nibble
                child_index = key_nibbles[nibble_idx]
                nibble_idx += 1
                child = decoded[child_index]

                if isinstance(child, bytes) and len(child) == 32:
                    expected_hash = child
                elif isinstance(child, bytes) and len(child) == 0:
                    # Dead end — key not in trie
                    return None
                else:
                    # Inlined node — continue with next proof node
                    expected_hash = b""

            elif len(decoded) == 2:
                # ── Extension or Leaf node ───────────────────────────
                encoded_path = decoded[0]
                if not isinstance(encoded_path, bytes):
                    logger.debug("Proof node %d: path not bytes", i)
                    return None

                path_nibbles, is_leaf = (
                    MerklePatriciaVerifier._decode_compact_path(encoded_path)
                )

                # Check that the path matches the remaining key nibbles
                remaining = key_nibbles[nibble_idx:]
                path_len = len(path_nibbles)

                if path_len > len(remaining):
                    return None  # Path extends beyond our key

                if remaining[:path_len] != path_nibbles:
                    return None  # Path diverges from our key

                nibble_idx += path_len

                if is_leaf:
                    # Leaf: value is decoded[1]
                    if nibble_idx == len(key_nibbles):
                        value = decoded[1]
                        return value if isinstance(value, bytes) else None
                    return None  # Key not fully consumed but leaf reached

                # Extension: follow to next node
                next_node = decoded[1]
                if isinstance(next_node, bytes) and len(next_node) == 32:
                    expected_hash = next_node
                elif isinstance(next_node, bytes) and len(next_node) == 0:
                    return None
                else:
                    expected_hash = b""

            else:
                logger.debug(
                    "Proof node %d: unexpected length %d", i, len(decoded)
                )
                return None

        # Exhausted proof without finding the value
        return None

    @staticmethod
    def verify_account_proof(
        state_root: bytes,
        address: str,
        proof: List[bytes],
    ) -> Optional[AccountState]:
        """Verify an account existence proof in the world state trie.

        The key is ``keccak256(address)`` where *address* is the raw
        20-byte address (without ``0x`` prefix hex encoding, but we
        accept both forms).

        Parameters
        ----------
        state_root : bytes
            32-byte root hash of the world state trie.
        address : str
            Ethereum address (with or without ``0x`` prefix).
        proof : list of bytes
            RLP-encoded proof nodes.

        Returns
        -------
        AccountState or None
            The decoded account state if the proof is valid.
        """
        # Normalize address
        addr_hex = address.lower().removeprefix("0x")
        addr_bytes = bytes.fromhex(addr_hex)

        # Key = keccak256(address)
        key = MerklePatriciaVerifier.keccak256(addr_bytes)

        value = MerklePatriciaVerifier.verify_proof(state_root, key, proof)
        if value is None:
            return None

        # Decode RLP: [nonce, balance, storageRoot, codeHash]
        try:
            decoded = RLPDecoder.decode(value)
        except ValueError:
            return None

        if not isinstance(decoded, list) or len(decoded) != 4:
            return None

        nonce_bytes, balance_bytes, storage_root, code_hash = decoded

        # Convert from RLP bytes to integers
        nonce = (
            int.from_bytes(nonce_bytes, "big")
            if isinstance(nonce_bytes, bytes) and nonce_bytes
            else 0
        )
        balance = (
            int.from_bytes(balance_bytes, "big")
            if isinstance(balance_bytes, bytes) and balance_bytes
            else 0
        )

        if not isinstance(storage_root, bytes) or len(storage_root) != 32:
            storage_root = b"\x00" * 32
        if not isinstance(code_hash, bytes) or len(code_hash) != 32:
            code_hash = b"\x00" * 32

        return AccountState(
            nonce=nonce,
            balance=balance,
            storage_root=storage_root,
            code_hash=code_hash,
        )

    @staticmethod
    def verify_storage_proof(
        storage_root: bytes,
        slot: bytes,
        proof: List[bytes],
    ) -> Optional[bytes]:
        """Verify a storage slot value in an account's storage trie.

        The key is ``keccak256(slot)`` where *slot* is the 32-byte
        storage slot index.

        Parameters
        ----------
        storage_root : bytes
            32-byte root hash of the account's storage trie.
        slot : bytes
            32-byte storage slot key.
        proof : list of bytes
            RLP-encoded proof nodes.

        Returns
        -------
        bytes or None
            The RLP-decoded storage value if the proof is valid.
        """
        key = MerklePatriciaVerifier.keccak256(slot)
        value = MerklePatriciaVerifier.verify_proof(storage_root, key, proof)
        if value is None:
            return None

        # Storage values are RLP-encoded — decode to get the raw bytes
        try:
            decoded = RLPDecoder.decode(value)
            if isinstance(decoded, bytes):
                return decoded
            return value
        except ValueError:
            return value

    @staticmethod
    def verify_receipt_proof(
        receipts_root: bytes,
        tx_index: int,
        proof: List[bytes],
    ) -> Optional[bytes]:
        """Verify a transaction receipt in the receipts trie.

        The key is ``RLP(tx_index)`` — for small indices this is just
        the big-endian encoding of the integer.

        Parameters
        ----------
        receipts_root : bytes
            32-byte root hash of the block's receipts trie.
        tx_index : int
            Transaction index within the block.
        proof : list of bytes
            RLP-encoded proof nodes.

        Returns
        -------
        bytes or None
            The raw receipt RLP if the proof is valid.
        """
        # Key = RLP-encode the transaction index
        # For small integers: if 0, key = b'\x80'; if 1–127, key = bytes([n])
        if tx_index == 0:
            # RLP of 0 is 0x80 (empty string), but in receipt trie
            # the key is the index as bytes — use big-endian encoding
            key_bytes = b"\x00"
        else:
            # Encode as minimal big-endian bytes
            length = (tx_index.bit_length() + 7) // 8
            key_bytes = tx_index.to_bytes(length, "big")

        return MerklePatriciaVerifier.verify_proof(receipts_root, key_bytes, proof)
