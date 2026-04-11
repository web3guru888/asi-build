"""
Rings Network ↔ Blackboard Adapter
=====================================

Bridges the Rings Network SDK (``asi_build.rings``) with the Cognitive
Blackboard, enabling P2P networking events to participate in the
cross-module integration layer.

Topics produced
~~~~~~~~~~~~~~~
- ``rings.peer.discovered``       — New peer found via Chord lookup
- ``rings.peer.connected``        — Peer session established
- ``rings.peer.disconnected``     — Peer session closed or timed out
- ``rings.did.authenticated``     — DID verification completed
- ``rings.did.created``           — New DID created locally
- ``rings.reputation.updated``    — Peer reputation score changed
- ``rings.reputation.slash``      — Slash report filed
- ``rings.subring.joined``        — Joined a Sub-Ring
- ``rings.subring.message``       — Message received from Sub-Ring
- ``rings.network.status``        — Periodic network health snapshot

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning.*``                 — Reasoning results to broadcast to Sub-Rings
- ``knowledge_graph.*``           — KG updates for DHT replication
- ``consciousness.*``             — Consciousness broadcasts → network relay

Events emitted
~~~~~~~~~~~~~~
- ``rings.peer.discovered``
- ``rings.did.authenticated``
- ``rings.did.failed``
- ``rings.reputation.threshold_crossed``
- ``rings.network.connected``
- ``rings.network.disconnected``

Events listened
~~~~~~~~~~~~~~~
- ``blackboard.entry.added``      — Selectively replicate entries to Sub-Rings
- ``reasoning.inference.completed``
- ``knowledge_graph.triple.added``
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

from ..protocols import (
    BlackboardEntry,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    EventHandler,
    ModuleCapability,
    ModuleInfo,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Topic ↔ Sub-Ring mapping
# ---------------------------------------------------------------------------

DEFAULT_TOPIC_SUBRING_MAP: Dict[str, str] = {
    "consciousness": "asi-build:consciousness",
    "reasoning": "asi-build:reasoning",
    "knowledge_graph": "asi-build:kg",
    "cognitive_synergy": "asi-build:synergy",
}


# ---------------------------------------------------------------------------
# RingsNetworkAdapter
# ---------------------------------------------------------------------------


class RingsNetworkAdapter:
    """Adapter connecting the Rings P2P network to the Cognitive Blackboard.

    Wraps three optional components:

    - ``RingsClient``       — DHT, Chord ring, Sub-Rings, sessions
    - ``RingsDID``          — DID identity management
    - ``ReputationClient``  — Ranking Protocol scoring

    If any component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    client : RingsClient, optional
        A connected (or connectable) Rings client.
    did_manager : RingsDID, optional
        DID identity manager.
    reputation : ReputationClient, optional
        Ranking Protocol reputation client.
    topic_subring_map : dict, optional
        Mapping from blackboard topic prefixes to Sub-Ring names.
    status_ttl : float
        TTL for network status entries (default 60s).
    reputation_ttl : float
        TTL for reputation update entries (default 300s).
    peer_ttl : float
        TTL for peer discovery entries (default 120s).
    """

    MODULE_NAME = "rings_network"
    MODULE_VERSION = "0.1.0"

    def __init__(
        self,
        client: Any = None,
        did_manager: Any = None,
        reputation: Any = None,
        *,
        topic_subring_map: Optional[Dict[str, str]] = None,
        status_ttl: float = 60.0,
        reputation_ttl: float = 300.0,
        peer_ttl: float = 120.0,
    ) -> None:
        self._client = client
        self._did_manager = did_manager
        self._reputation = reputation
        self._topic_map = topic_subring_map or dict(DEFAULT_TOPIC_SUBRING_MAP)

        self._status_ttl = status_ttl
        self._reputation_ttl = reputation_ttl
        self._peer_ttl = peer_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # State tracking
        self._connected = False
        self._authenticated_peers: Set[str] = set()
        self._joined_subrings: Set[str] = set()
        self._last_status_snapshot: Optional[Dict[str, Any]] = None
        self._reputation_cache: Dict[str, float] = {}  # did → score

    # ── BlackboardParticipant protocol ────────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER
                | ModuleCapability.CONSUMER
                | ModuleCapability.TRANSFORMER
            ),
            description=(
                "Rings Network P2P adapter: DID authentication, Chord DHT, "
                "Sub-Ring messaging, and Ranking Protocol reputation."
            ),
            topics_produced=frozenset(
                {
                    "rings.peer",
                    "rings.did",
                    "rings.reputation",
                    "rings.subring",
                    "rings.network",
                }
            ),
            topics_consumed=frozenset(
                {
                    "reasoning",
                    "knowledge_graph",
                    "consciousness",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "RingsNetworkAdapter registered with blackboard "
            "(client=%s, did=%s, reputation=%s)",
            self._client is not None,
            self._did_manager is not None,
            self._reputation is not None,
        )

    # ── EventEmitter protocol ─────────────────────────────────────────────

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

    # ── EventListener protocol ────────────────────────────────────────────

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle incoming events from other modules.

        Selectively replicates relevant events to the P2P network
        via Sub-Ring broadcasts.
        """
        if self._client is None:
            return

        try:
            # Determine which sub-ring to relay to
            prefix = event.event_type.split(".")[0]
            subring = self._topic_map.get(prefix)
            if subring and subring in self._joined_subrings:
                self._schedule_broadcast(subring, {
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "source": event.source,
                    "timestamp": event.timestamp,
                })
        except Exception:
            logger.debug(
                "RingsNetworkAdapter: failed to relay event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current network state.

        Called during a production sweep. Collects:
        1. Network status snapshot
        2. Reputation updates (if changed)
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            status_entry = self._produce_network_status()
            if status_entry is not None:
                entries.append(status_entry)

            rep_entries = self._produce_reputation_updates()
            entries.extend(rep_entries)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        Entries from reasoning / KG / consciousness are candidates for
        DHT replication or Sub-Ring broadcast.
        """
        for entry in entries:
            try:
                prefix = entry.topic.split(".")[0]
                if prefix in self._topic_map:
                    self._queue_for_replication(entry)
            except Exception:
                logger.debug(
                    "RingsNetworkAdapter: failed to consume entry %s",
                    entry.entry_id,
                    exc_info=True,
                )

    # ── BlackboardTransformer protocol ────────────────────────────────────

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Enrich entries with Rings network metadata.

        Adds: reputation score of source, DID verification status,
        P2P routing info.
        """
        if self._reputation is None:
            return []

        result: List[BlackboardEntry] = []
        for entry in entries:
            enriched = self._enrich_with_reputation(entry)
            if enriched is not None:
                result.append(enriched)
        return result

    # ── Peer Discovery & Authentication ───────────────────────────────────

    def record_peer_discovery(
        self,
        peer_did: str,
        position: int = 0,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> BlackboardEntry:
        """Record a new peer discovery event.

        Parameters
        ----------
        peer_did : str
            DID of the discovered peer.
        position : int
            Chord ring position.
        capabilities : dict, optional
            Peer's advertised capabilities.

        Returns
        -------
        BlackboardEntry
            The entry posted to the blackboard.
        """
        entry = BlackboardEntry(
            topic="rings.peer.discovered",
            data={
                "peer_did": peer_did,
                "position": position,
                "capabilities": capabilities or {},
                "discovered_at": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.8,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._peer_ttl,
            tags=frozenset({"peer", "discovery", "rings"}),
        )

        self._emit("rings.peer.discovered", {
            "peer_did": peer_did,
            "entry_id": entry.entry_id,
        })
        return entry

    def record_did_authentication(
        self,
        peer_did: str,
        success: bool,
        trust_tier: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> BlackboardEntry:
        """Record a DID authentication result.

        Parameters
        ----------
        peer_did : str
            DID of the authenticated peer.
        success : bool
            Whether authentication succeeded.
        trust_tier : str
            Derived trust level.
        details : dict, optional
            Additional authentication details.

        Returns
        -------
        BlackboardEntry
        """
        topic = "rings.did.authenticated" if success else "rings.did.failed"
        confidence = 0.95 if success else 0.3

        with self._lock:
            if success:
                self._authenticated_peers.add(peer_did)
            else:
                self._authenticated_peers.discard(peer_did)

        entry = BlackboardEntry(
            topic=topic,
            data={
                "peer_did": peer_did,
                "authenticated": success,
                "trust_tier": trust_tier,
                "details": details or {},
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=confidence,
            priority=EntryPriority.HIGH if not success else EntryPriority.NORMAL,
            ttl_seconds=self._peer_ttl,
            tags=frozenset({"did", "authentication", "rings"}),
        )

        event_type = "rings.did.authenticated" if success else "rings.did.failed"
        self._emit(event_type, {
            "peer_did": peer_did,
            "success": success,
            "entry_id": entry.entry_id,
        })
        return entry

    def record_reputation_update(
        self,
        peer_did: str,
        score: float,
        previous_score: Optional[float] = None,
    ) -> BlackboardEntry:
        """Record a reputation score change for a peer.

        Parameters
        ----------
        peer_did : str
            DID of the scored peer.
        score : float
            New reputation score [0, 1].
        previous_score : float, optional
            Previous score (for change detection).

        Returns
        -------
        BlackboardEntry
        """
        with self._lock:
            old_score = self._reputation_cache.get(peer_did, previous_score)
            self._reputation_cache[peer_did] = score

        entry = BlackboardEntry(
            topic="rings.reputation.updated",
            data={
                "peer_did": peer_did,
                "score": score,
                "previous_score": old_score,
                "delta": score - old_score if old_score is not None else None,
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._reputation_ttl,
            tags=frozenset({"reputation", "ranking", "rings"}),
        )

        # Check for threshold crossing
        threshold = 0.5  # Default trust threshold
        if old_score is not None:
            crossed_up = old_score < threshold <= score
            crossed_down = score < threshold <= old_score
            if crossed_up or crossed_down:
                self._emit("rings.reputation.threshold_crossed", {
                    "peer_did": peer_did,
                    "score": score,
                    "direction": "up" if crossed_up else "down",
                    "threshold": threshold,
                })

        return entry

    def record_slash(
        self,
        target_did: str,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> BlackboardEntry:
        """Record a slash report against a peer.

        Parameters
        ----------
        target_did : str
            DID of the malicious peer.
        reason : str
            Description of misbehaviour.
        evidence : dict, optional
            Supporting evidence.

        Returns
        -------
        BlackboardEntry
        """
        entry = BlackboardEntry(
            topic="rings.reputation.slash",
            data={
                "target_did": target_did,
                "reporter_did": getattr(self._reputation, "local_did", ""),
                "reason": reason,
                "evidence": evidence or {},
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.7,
            priority=EntryPriority.HIGH,
            ttl_seconds=self._reputation_ttl,
            tags=frozenset({"reputation", "slash", "rings", "security"}),
        )
        return entry

    # ── Sub-Ring Events ───────────────────────────────────────────────────

    def record_subring_join(self, topic: str, member_count: int = 0) -> BlackboardEntry:
        """Record joining a Sub-Ring."""
        with self._lock:
            self._joined_subrings.add(topic)

        entry = BlackboardEntry(
            topic="rings.subring.joined",
            data={
                "subring_topic": topic,
                "member_count": member_count,
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=1.0,
            priority=EntryPriority.LOW,
            ttl_seconds=self._status_ttl,
            tags=frozenset({"subring", "rings"}),
        )
        return entry

    def record_subring_message(
        self,
        topic: str,
        message: Any,
        sender_did: str = "",
    ) -> BlackboardEntry:
        """Record an incoming Sub-Ring broadcast message."""
        entry = BlackboardEntry(
            topic="rings.subring.message",
            data={
                "subring_topic": topic,
                "message": message,
                "sender_did": sender_did,
                "received_at": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.8,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._peer_ttl,
            tags=frozenset({"subring", "message", "rings"}),
        )
        return entry

    # ── Producer helpers ──────────────────────────────────────────────────

    def _produce_network_status(self) -> Optional[BlackboardEntry]:
        """Produce a network health snapshot.

        Only posts if the status changed from the last snapshot.
        """
        status: Dict[str, Any] = {
            "connected": self._connected,
            "peer_count": len(self._authenticated_peers),
            "subring_count": len(self._joined_subrings),
            "subrings": sorted(self._joined_subrings),
            "timestamp": time.time(),
        }

        if self._client is not None:
            status["client_state"] = getattr(
                self._client, "state", "unknown"
            )
            if hasattr(self._client.state, "value"):
                status["client_state"] = self._client.state.value
            status["endpoint"] = getattr(self._client, "endpoint", "")

        # Change detection
        if self._last_status_snapshot is not None:
            # Compare key fields
            if (
                self._last_status_snapshot.get("connected") == status["connected"]
                and self._last_status_snapshot.get("peer_count") == status["peer_count"]
                and self._last_status_snapshot.get("subring_count") == status["subring_count"]
            ):
                return None

        self._last_status_snapshot = status

        entry = BlackboardEntry(
            topic="rings.network.status",
            data=status,
            source_module=self.MODULE_NAME,
            confidence=1.0,
            priority=EntryPriority.LOW,
            ttl_seconds=self._status_ttl,
            tags=frozenset({"network", "status", "rings"}),
        )

        event_type = "rings.network.connected" if self._connected else "rings.network.disconnected"
        self._emit(event_type, {"entry_id": entry.entry_id})
        return entry

    def _produce_reputation_updates(self) -> List[BlackboardEntry]:
        """Produce entries for any reputation changes."""
        if self._reputation is None:
            return []

        entries: List[BlackboardEntry] = []
        try:
            all_ranks = self._reputation.get_all_local_ranks()
            for did, record in all_ranks.items():
                cached = self._reputation_cache.get(did)
                if cached is None or abs(cached - record.score) > 0.05:
                    entry = self.record_reputation_update(
                        peer_did=did,
                        score=record.score,
                        previous_score=cached,
                    )
                    entries.append(entry)
        except Exception:
            logger.debug("Failed to produce reputation updates", exc_info=True)
        return entries

    # ── Consumer helpers ──────────────────────────────────────────────────

    def _queue_for_replication(self, entry: BlackboardEntry) -> None:
        """Mark an entry for DHT/Sub-Ring replication.

        In a fully async implementation, this would schedule an async
        task to broadcast or replicate the entry via the Rings client.
        For now, we record the intent.
        """
        prefix = entry.topic.split(".")[0]
        subring = self._topic_map.get(prefix)
        if subring:
            logger.debug(
                "Queued entry %s (topic=%s) for Sub-Ring %s",
                entry.entry_id,
                entry.topic,
                subring,
            )

    def _schedule_broadcast(self, subring: str, message: Dict[str, Any]) -> None:
        """Schedule an async broadcast to a Sub-Ring.

        In production, this would use asyncio.create_task() with the
        actual RingsClient.broadcast() call.
        """
        logger.debug("Scheduled broadcast to Sub-Ring %s: %s", subring, message.get("event_type"))

    # ── Transformer helpers ───────────────────────────────────────────────

    def _enrich_with_reputation(self, entry: BlackboardEntry) -> Optional[BlackboardEntry]:
        """Enrich an entry with the source module's reputation info."""
        if self._reputation is None:
            return None

        # Check if the source has a known DID
        source = entry.source_module
        # Simple heuristic: map module name to a DID (in production,
        # module registration would include DID)
        rep_score = None
        for did, score in self._reputation_cache.items():
            if source in did:
                rep_score = score
                break

        if rep_score is None:
            return None

        # Create enriched entry
        enriched = BlackboardEntry(
            topic=entry.topic,
            data=entry.data,
            source_module=self.MODULE_NAME,
            confidence=entry.confidence,
            priority=entry.priority,
            ttl_seconds=entry.ttl_seconds,
            tags=entry.tags | frozenset({"rings-enriched"}),
            parent_id=entry.entry_id,
            metadata={
                **entry.metadata,
                "rings_reputation": rep_score,
                "rings_enriched_at": time.time(),
            },
        )
        return enriched

    # ── Connection state management ───────────────────────────────────────

    def set_connected(self, connected: bool) -> None:
        """Update connection state (called by higher-level orchestration)."""
        with self._lock:
            self._connected = connected
            # Reset snapshot so next produce() will emit status
            self._last_status_snapshot = None

    # ── Convenience snapshot ──────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a diagnostic snapshot of the adapter state."""
        with self._lock:
            return {
                "module": self.MODULE_NAME,
                "connected": self._connected,
                "has_client": self._client is not None,
                "has_did_manager": self._did_manager is not None,
                "has_reputation": self._reputation is not None,
                "authenticated_peers": len(self._authenticated_peers),
                "joined_subrings": sorted(self._joined_subrings),
                "reputation_cache_size": len(self._reputation_cache),
                "registered": self._blackboard is not None,
                "topic_subring_map": dict(self._topic_map),
            }
