"""
Blockchain ↔ Blackboard Adapter
===================================

Bridges the blockchain module (``HashManager``, ``MerkleTree``, ``HashChain``,
``SignatureManager``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``blockchain.hash_verification``  — Hash verification results for data integrity
- ``blockchain.merkle_proof``       — Merkle tree proofs and root hashes
- ``blockchain.chain_status``       — Hash chain status and integrity
- ``blockchain.audit_log``          — Audit trail of cryptographic operations

Topics consumed
~~~~~~~~~~~~~~~
- ``knowledge_graph``               — KG triples → hash for tamper detection
- ``reasoning``                     — Reasoning outputs → chain for auditability
- ``compute``                       — Compute results → Merkle-tree integrity proofs

Events emitted
~~~~~~~~~~~~~~
- ``blockchain.chain.verified``         — Hash chain integrity verification passed
- ``blockchain.integrity.violation``    — Integrity violation detected

Events listened
~~~~~~~~~~~~~~~
- ``knowledge_graph.triple.added``      — Hash new triples for tamper detection
- ``reasoning.inference.completed``     — Add inference to audit chain
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Sequence

from ..protocols import (
    BlackboardEntry,
    BlackboardQuery,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    EventHandler,
    ModuleCapability,
    ModuleInfo,
)

logger = logging.getLogger(__name__)

_blockchain_module = None


def _get_blockchain():
    """Lazy import of blockchain module to allow graceful degradation."""
    global _blockchain_module
    if _blockchain_module is None:
        try:
            from asi_build import blockchain as _bm

            _blockchain_module = _bm
        except (ImportError, ModuleNotFoundError):
            _blockchain_module = False
    return _blockchain_module if _blockchain_module is not False else None


class BlockchainBlackboardAdapter:
    """Adapter connecting the blockchain module to the Cognitive Blackboard.

    Wraps up to four components:

    - ``HashManager`` — hash computation and verification
    - ``MerkleTree`` — Merkle tree construction and proof generation
    - ``HashChain`` — append-only hash chain for audit trails
    - ``SignatureManager`` — digital signature generation and verification

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    hash_manager : optional
        A ``HashManager`` instance.
    merkle_tree : optional
        A ``MerkleTree`` instance.
    hash_chain : optional
        A ``HashChain`` instance.
    signature_manager : optional
        A ``SignatureManager`` instance.
    hash_verification_ttl : float
        TTL in seconds for hash verification entries (default 300).
    merkle_proof_ttl : float
        TTL for Merkle proof entries (default 600).
    chain_status_ttl : float
        TTL for chain status entries (default 120).
    audit_log_ttl : float
        TTL for audit log entries (default 600).
    """

    MODULE_NAME = "blockchain"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        hash_manager: Any = None,
        merkle_tree: Any = None,
        hash_chain: Any = None,
        signature_manager: Any = None,
        *,
        hash_verification_ttl: float = 300.0,
        merkle_proof_ttl: float = 600.0,
        chain_status_ttl: float = 120.0,
        audit_log_ttl: float = 600.0,
    ) -> None:
        self._hash_manager = hash_manager
        self._merkle_tree = merkle_tree
        self._hash_chain = hash_chain
        self._signature_manager = signature_manager
        self._hash_verification_ttl = hash_verification_ttl
        self._merkle_proof_ttl = merkle_proof_ttl
        self._chain_status_ttl = chain_status_ttl
        self._audit_log_ttl = audit_log_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change detection and audit state
        self._last_chain_length: int = 0
        self._last_root_hash: Optional[str] = None
        self._last_chain_valid: Optional[bool] = None
        self._audit_buffer: List[Dict[str, Any]] = []
        self._max_audit_buffer: int = 50

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER | ModuleCapability.CONSUMER
            ),
            description=(
                "Blockchain integrity: hash verification, Merkle proofs, "
                "hash chain audit trails, and digital signatures."
            ),
            topics_produced=frozenset(
                {
                    "blockchain.hash_verification",
                    "blockchain.merkle_proof",
                    "blockchain.chain_status",
                    "blockchain.audit_log",
                }
            ),
            topics_consumed=frozenset(
                {
                    "knowledge_graph",
                    "reasoning",
                    "compute",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "BlockchainBlackboardAdapter registered with blackboard "
            "(hash_manager=%s, merkle_tree=%s, hash_chain=%s, signature_manager=%s)",
            self._hash_manager is not None,
            self._merkle_tree is not None,
            self._hash_chain is not None,
            self._signature_manager is not None,
        )

    # ── EventEmitter protocol ─────────────────────────────────────────

    def set_event_handler(self, handler: EventHandler) -> None:
        self._event_handler = handler

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit an event via the injected handler."""
        if self._event_handler is not None:
            self._event_handler(
                CognitiveEvent(
                    event_type=event_type,
                    payload=payload,
                    source=self.MODULE_NAME,
                )
            )

    # ── EventListener protocol ────────────────────────────────────────

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle incoming events from other modules."""
        try:
            if event.event_type.startswith("knowledge_graph."):
                self._handle_kg_event(event)
            elif event.event_type.startswith("reasoning."):
                self._handle_reasoning_event(event)
        except Exception:
            logger.debug(
                "BlockchainBlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current blockchain state."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            chain_entry = self._produce_chain_status()
            if chain_entry is not None:
                entries.append(chain_entry)

            merkle_entry = self._produce_merkle_proof()
            if merkle_entry is not None:
                entries.append(merkle_entry)

            audit_entries = self._produce_audit_log()
            entries.extend(audit_entries)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        KG triples → hash for tamper detection.
        Reasoning outputs → add to hash chain for auditability.
        Compute results → Merkle-tree integrity proofs.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("knowledge_graph."):
                    self._consume_kg(entry)
                elif entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("compute."):
                    self._consume_compute(entry)
            except Exception:
                logger.debug(
                    "BlockchainBlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_chain_status(self) -> Optional[BlackboardEntry]:
        """Verify hash chain integrity and report status."""
        if self._hash_chain is None:
            return None

        try:
            # Get chain summary
            summary_fn = getattr(self._hash_chain, "get_chain_summary", None)
            if summary_fn is not None:
                chain_data = summary_fn()
            else:
                chain_data = {}

            if not isinstance(chain_data, dict):
                chain_data = {"raw": str(chain_data)}

            # Verify chain integrity
            verify_fn = getattr(self._hash_chain, "verify_chain", None)
            chain_valid = None
            if verify_fn is not None:
                chain_valid = verify_fn()
                chain_data["chain_valid"] = chain_valid

            # Get chain length
            chain_blocks = getattr(self._hash_chain, "chain", None)
            chain_length = len(chain_blocks) if chain_blocks is not None and hasattr(chain_blocks, '__len__') else 0
            chain_data["chain_length"] = chain_length

        except Exception:
            logger.debug("HashChain status check failed", exc_info=True)
            return None

        # Change detection: only post if chain length or validity changed
        if chain_length == self._last_chain_length and chain_valid == self._last_chain_valid:
            return None

        prev_valid = self._last_chain_valid
        self._last_chain_length = chain_length
        self._last_chain_valid = chain_valid

        # Determine priority based on integrity
        if chain_valid is False:
            priority = EntryPriority.CRITICAL
        elif chain_length > 1000:
            priority = EntryPriority.HIGH
        else:
            priority = EntryPriority.NORMAL

        entry = BlackboardEntry(
            topic="blockchain.chain_status",
            data=chain_data,
            source_module=self.MODULE_NAME,
            confidence=0.99 if chain_valid else 0.5,
            priority=priority,
            ttl_seconds=self._chain_status_ttl,
            tags=frozenset({"blockchain", "chain", "integrity", "audit"}),
            metadata={
                "chain_length": chain_length,
                "chain_valid": chain_valid,
            },
        )

        if chain_valid is True:
            self._emit(
                "blockchain.chain.verified",
                {
                    "chain_length": chain_length,
                    "entry_id": entry.entry_id,
                },
            )
        elif chain_valid is False and prev_valid is not False:
            self._emit(
                "blockchain.integrity.violation",
                {
                    "chain_length": chain_length,
                    "chain_data": chain_data,
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    def _produce_merkle_proof(self) -> Optional[BlackboardEntry]:
        """Produce Merkle tree root hash and tree statistics."""
        if self._merkle_tree is None:
            return None

        try:
            root_fn = getattr(self._merkle_tree, "get_root_hash", None)
            if root_fn is None:
                return None
            root_hash = root_fn()
        except Exception:
            logger.debug("MerkleTree get_root_hash() failed", exc_info=True)
            return None

        if root_hash is None:
            return None

        # Change detection: only post if root hash changed
        if root_hash == self._last_root_hash:
            return None
        self._last_root_hash = root_hash

        merkle_data: Dict[str, Any] = {"root_hash": root_hash}

        # Try to get leaf count
        leaves = getattr(self._merkle_tree, "leaves", None)
        if leaves is not None and hasattr(leaves, '__len__'):
            merkle_data["leaf_count"] = len(leaves)

        # Try to get tree depth
        nodes = getattr(self._merkle_tree, "nodes", None)
        if nodes is not None and hasattr(nodes, '__len__'):
            merkle_data["node_count"] = len(nodes)

        entry = BlackboardEntry(
            topic="blockchain.merkle_proof",
            data=merkle_data,
            source_module=self.MODULE_NAME,
            confidence=0.99,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._merkle_proof_ttl,
            tags=frozenset({"blockchain", "merkle", "proof", "root_hash"}),
            metadata={"root_hash": root_hash[:16] + "..." if len(root_hash) > 16 else root_hash},
        )

        return entry

    def _produce_audit_log(self) -> List[BlackboardEntry]:
        """Flush buffered audit entries as blackboard entries."""
        if not self._audit_buffer:
            return []

        entries: List[BlackboardEntry] = []
        buffer_to_post = list(self._audit_buffer)
        self._audit_buffer.clear()

        for audit_item in buffer_to_post:
            entries.append(
                BlackboardEntry(
                    topic="blockchain.audit_log",
                    data=audit_item,
                    source_module=self.MODULE_NAME,
                    confidence=0.95,
                    priority=EntryPriority.LOW,
                    ttl_seconds=self._audit_log_ttl,
                    tags=frozenset({"blockchain", "audit", "log", audit_item.get("operation", "unknown")}),
                    metadata={"operation": audit_item.get("operation", "unknown")},
                )
            )

        return entries

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Hash KG triples for tamper detection and add to chain."""
        data = entry.data if isinstance(entry.data, dict) else {}

        # Hash the triple data
        triple_text = json.dumps(data, sort_keys=True, default=str)

        if self._hash_manager is not None:
            try:
                hash_fn = getattr(self._hash_manager, "hash_data", None)
                if hash_fn is not None:
                    result = hash_fn(triple_text)
                    self._record_audit("hash_kg_triple", {
                        "entry_id": entry.entry_id,
                        "hash": getattr(result, "hash_value", str(result)),
                    })
            except Exception:
                logger.debug("Failed to hash KG triple", exc_info=True)

        # Add to hash chain
        if self._hash_chain is not None:
            try:
                add_fn = getattr(self._hash_chain, "add_block", None)
                if add_fn is not None:
                    add_fn(triple_text)
            except Exception:
                logger.debug("Failed to add KG triple to chain", exc_info=True)

        # Add to Merkle tree
        if self._merkle_tree is not None:
            try:
                add_data_fn = getattr(self._merkle_tree, "add_data", None)
                if add_data_fn is not None:
                    add_data_fn(triple_text)
            except Exception:
                logger.debug("Failed to add KG triple to Merkle tree", exc_info=True)

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Add reasoning outputs to the audit chain."""
        if self._hash_chain is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        audit_data = json.dumps({
            "type": "reasoning_inference",
            "entry_id": entry.entry_id,
            "confidence": entry.confidence,
            "data_hash": hashlib.sha256(
                json.dumps(data, sort_keys=True, default=str).encode()
            ).hexdigest()[:16],
            "timestamp": time.time(),
        }, sort_keys=True)

        try:
            add_fn = getattr(self._hash_chain, "add_block", None)
            if add_fn is not None:
                block_hash = add_fn(audit_data)
                self._record_audit("chain_reasoning", {
                    "entry_id": entry.entry_id,
                    "block_hash": str(block_hash) if block_hash else None,
                })
        except Exception:
            logger.debug("Failed to chain reasoning output", exc_info=True)

    def _consume_compute(self, entry: BlackboardEntry) -> None:
        """Add compute results to Merkle tree for integrity proofs."""
        if self._merkle_tree is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        compute_text = json.dumps(data, sort_keys=True, default=str)
        try:
            add_data_fn = getattr(self._merkle_tree, "add_data", None)
            if add_data_fn is not None:
                add_data_fn(compute_text)
                self._record_audit("merkle_compute", {
                    "entry_id": entry.entry_id,
                })
        except Exception:
            logger.debug("Failed to add compute result to Merkle tree", exc_info=True)

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_kg_event(self, event: CognitiveEvent) -> None:
        """Hash new KG triples for tamper detection on event notification."""
        if self._hash_manager is None and self._hash_chain is None:
            return
        payload = event.payload or {}
        text = json.dumps(payload, sort_keys=True, default=str)

        if self._hash_chain is not None:
            try:
                add_fn = getattr(self._hash_chain, "add_block", None)
                if add_fn is not None:
                    add_fn(text)
            except Exception:
                pass

    def _handle_reasoning_event(self, event: CognitiveEvent) -> None:
        """Add completed inferences to the audit chain."""
        if self._hash_chain is None:
            return
        payload = event.payload or {}
        audit_data = json.dumps({
            "type": "reasoning_event",
            "event_id": event.event_id,
            "payload_hash": hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()
            ).hexdigest()[:16],
        }, sort_keys=True)

        try:
            add_fn = getattr(self._hash_chain, "add_block", None)
            if add_fn is not None:
                add_fn(audit_data)
        except Exception:
            pass

    # ── Internal helpers ──────────────────────────────────────────────

    def _record_audit(self, operation: str, details: Dict[str, Any]) -> None:
        """Buffer an audit record for the next production sweep."""
        with self._lock:
            if len(self._audit_buffer) >= self._max_audit_buffer:
                # Evict oldest entries
                self._audit_buffer = self._audit_buffer[-(self._max_audit_buffer // 2):]
            self._audit_buffer.append({
                "operation": operation,
                "timestamp": time.time(),
                **details,
            })

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all blockchain components."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_hash_manager": self._hash_manager is not None,
            "has_merkle_tree": self._merkle_tree is not None,
            "has_hash_chain": self._hash_chain is not None,
            "has_signature_manager": self._signature_manager is not None,
            "last_chain_length": self._last_chain_length,
            "last_chain_valid": self._last_chain_valid,
            "last_root_hash": self._last_root_hash,
            "audit_buffer_size": len(self._audit_buffer),
            "registered": self._blackboard is not None,
        }

        if self._hash_chain is not None:
            try:
                verify_fn = getattr(self._hash_chain, "verify_chain", None)
                if verify_fn is not None:
                    snap["current_chain_valid"] = verify_fn()
                summary_fn = getattr(self._hash_chain, "get_chain_summary", None)
                if summary_fn is not None:
                    snap["chain_summary"] = summary_fn()
            except Exception:
                snap["current_chain_valid"] = None

        if self._merkle_tree is not None:
            try:
                root_fn = getattr(self._merkle_tree, "get_root_hash", None)
                if root_fn is not None:
                    snap["current_root_hash"] = root_fn()
            except Exception:
                snap["current_root_hash"] = None

        if self._signature_manager is not None:
            try:
                list_fn = getattr(self._signature_manager, "list_key_pairs", None)
                if list_fn is not None:
                    snap["key_pair_count"] = len(list_fn())
            except Exception:
                pass

        return snap
