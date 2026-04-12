"""
Rings Network Python SDK — Client
===================================

Thin async wrapper around a Rings Network node's JSON-RPC / WebSocket
interface.  The client is transport-agnostic: when a live Rings node is
available it speaks over WebSocket; for testing it falls back to in-memory
mocks injected via the ``transport`` parameter.

The Rings Network is a Chord-based, DID-authenticated P2P overlay running
in Rust / WASM.  This client implements **only the RPC calls** — it does
not embed a full node.

Architecture (from the Rings paper, 5-layer stack)::

    Application  ← this SDK lives here (JSON-RPC / FFI)
    Protocol     ← DID, sessions, VIDs
    Network      ← Chord DHT, finger tables
    Transport    ← WebRTC / DTLS
    Runtime      ← Rust / WASM

All methods are ``async`` so callers can run them in any event loop.
"""

from __future__ import annotations

import asyncio
import enum
import hashlib
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RING_MODULUS = 2**160  # Chord ring operates in Z_{2^160}
DEFAULT_REPLICATION = 6  # DHash: 6 replicas per block
DEFAULT_RPC_TIMEOUT = 30.0  # seconds


# ---------------------------------------------------------------------------
# Transport abstraction
# ---------------------------------------------------------------------------


@runtime_checkable
class RingsTransport(Protocol):
    """Transport protocol — anything that can send JSON-RPC calls."""

    async def connect(self, endpoint: str) -> None: ...
    async def disconnect(self) -> None: ...
    async def call(self, method: str, params: Dict[str, Any]) -> Any: ...

    @property
    def is_connected(self) -> bool: ...


class InMemoryTransport:
    """In-process mock transport for testing (no network)."""

    def __init__(self) -> None:
        self._connected = False
        self._store: Dict[str, Any] = {}
        self._peers: Dict[str, Dict[str, Any]] = {}
        self._sub_rings: Dict[str, List[str]] = {}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._finger_table: List[Dict[str, Any]] = []

    async def connect(self, endpoint: str) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def call(self, method: str, params: Dict[str, Any]) -> Any:
        if not self._connected:
            raise ConnectionError("Transport not connected")

        # Route to handler
        handler = getattr(self, f"_handle_{method}", None)
        if handler is not None:
            return await handler(params)
        raise ValueError(f"Unknown RPC method: {method}")

    # -- DHT operations ---------------------------------------------------

    async def _handle_dht_put(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params["key"]
        value = params["value"]
        operator = params.get("operator", "Overwrite")
        if operator == "Extend" and key in self._store:
            existing = self._store[key]
            if isinstance(existing, list):
                if isinstance(value, list):
                    existing.extend(value)
                else:
                    existing.append(value)
            else:
                if isinstance(value, list):
                    self._store[key] = [existing] + value
                else:
                    self._store[key] = [existing, value]
        else:
            self._store[key] = value
        return {"ok": True, "key": key}

    async def _handle_dht_get(self, params: Dict[str, Any]) -> Any:
        key = params["key"]
        return self._store.get(key)

    async def _handle_dht_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params["key"]
        removed = self._store.pop(key, None) is not None
        return {"ok": removed, "key": key}

    # -- Peer operations --------------------------------------------------

    async def _handle_ring_join(self, params: Dict[str, Any]) -> Dict[str, Any]:
        did = params.get("did", "did:rings:local")
        self._peers[did] = {"did": did, "joined_at": time.time()}
        return {"ok": True, "did": did, "position": _did_to_position(did)}

    async def _handle_ring_find_successor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        target_id = int(params["id"])
        # In a real Chord ring this would hop; mock returns self
        return {"did": "did:rings:mock_successor", "position": target_id % RING_MODULUS}

    async def _handle_ring_finger_table(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Mock: return a simple 160-entry finger table
        if not self._finger_table:
            self._finger_table = [
                {"index": i, "start": (2**i) % RING_MODULUS, "node": f"did:rings:finger_{i}"}
                for i in range(160)
            ]
        return self._finger_table

    async def _handle_ring_peers(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return list(self._peers.values())

    # -- Sub-Ring operations ----------------------------------------------

    async def _handle_subring_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        topic = params["topic"]
        self._sub_rings.setdefault(topic, [])
        vid = _compute_vid(topic)
        return {"ok": True, "topic": topic, "vid": vid}

    async def _handle_subring_join(self, params: Dict[str, Any]) -> Dict[str, Any]:
        topic = params["topic"]
        did = params.get("did", "did:rings:local")
        self._sub_rings.setdefault(topic, []).append(did)
        return {"ok": True, "topic": topic, "member_count": len(self._sub_rings[topic])}

    async def _handle_subring_leave(self, params: Dict[str, Any]) -> Dict[str, Any]:
        topic = params["topic"]
        did = params.get("did", "did:rings:local")
        members = self._sub_rings.get(topic, [])
        if did in members:
            members.remove(did)
        return {"ok": True, "topic": topic}

    async def _handle_subring_members(self, params: Dict[str, Any]) -> List[str]:
        topic = params["topic"]
        return list(self._sub_rings.get(topic, []))

    async def _handle_subring_broadcast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        topic = params["topic"]
        message = params["message"]
        members = self._sub_rings.get(topic, [])
        return {"ok": True, "recipients": len(members), "topic": topic}

    # -- Session operations -----------------------------------------------

    async def _handle_session_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        peer_did = params["peer_did"]
        session_id = uuid.uuid4().hex[:16]
        self._sessions[session_id] = {
            "session_id": session_id,
            "peer_did": peer_did,
            "created_at": time.time(),
            "messages": [],
        }
        return {"session_id": session_id, "peer_did": peer_did}

    async def _handle_session_send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        session_id = params["session_id"]
        data = params["data"]
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")
        session["messages"].append({"direction": "out", "data": data, "ts": time.time()})
        return {"ok": True, "session_id": session_id}

    async def _handle_session_receive(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session_id = params["session_id"]
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")
        inbox = [m for m in session["messages"] if m["direction"] == "in"]
        return inbox[-1] if inbox else None

    async def _handle_session_close(self, params: Dict[str, Any]) -> Dict[str, Any]:
        session_id = params["session_id"]
        self._sessions.pop(session_id, None)
        return {"ok": True}

    # -- DID operations ---------------------------------------------------

    async def _handle_did_resolve(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        did = params["did"]
        peer = self._peers.get(did)
        if peer is None:
            return None
        return {
            "id": did,
            "verificationMethod": [
                {
                    "id": f"{did}#key-1",
                    "type": "EcdsaSecp256k1VerificationKey2019",
                    "controller": did,
                    "publicKeyHex": hashlib.sha256(did.encode()).hexdigest(),
                }
            ],
            "service": [],
        }

    async def _handle_did_lookup(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self._handle_did_resolve(params)

    # -- Node info --------------------------------------------------------

    async def _handle_node_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "version": "0.1.0-mock",
            "did": "did:rings:local",
            "position": 0,
            "uptime": 0,
            "peer_count": len(self._peers),
        }


# ---------------------------------------------------------------------------
# Enums & data types
# ---------------------------------------------------------------------------


class ConnectionState(enum.Enum):
    """Client connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class DHTOperator(enum.Enum):
    """VID storage operators (from Rings paper §4.2)."""

    OVERWRITE = "Overwrite"  # Replace value
    EXTEND = "Extend"  # Append to existing
    TOUCH = "Touch"  # Update TTL only
    JOIN_SUBRING = "JoinSubRing"  # Join a Sub-Ring at the VID


@dataclass
class PeerInfo:
    """Information about a connected peer."""

    did: str
    position: int = 0
    joined_at: float = field(default_factory=time.time)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    reputation: float = 0.0


@dataclass
class SubRingInfo:
    """Metadata about a Sub-Ring (topic partition)."""

    topic: str
    vid: str = ""
    member_count: int = 0
    joined: bool = False


@dataclass
class SessionInfo:
    """An E2E encrypted session with a peer."""

    session_id: str
    peer_did: str
    created_at: float = field(default_factory=time.time)
    is_active: bool = True


@dataclass
class FingerEntry:
    """One row of the Chord finger table."""

    index: int
    start: int  # (self + 2^i) mod 2^160
    node_did: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _did_to_position(did: str) -> int:
    """Map a DID string to a position on the Chord ring (Z_{2^160})."""
    h = hashlib.sha1(did.encode()).digest()  # 160-bit hash
    return int.from_bytes(h, "big") % RING_MODULUS


def _compute_vid(name: str) -> str:
    """Compute a Virtual DID (VID) — H(name) → hex string."""
    h = hashlib.sha1(name.encode()).hexdigest()
    return f"vid:{h}"


# ---------------------------------------------------------------------------
# RingsClient
# ---------------------------------------------------------------------------


class RingsClient:
    """Async client for communicating with a Rings Network node.

    Parameters
    ----------
    endpoint : str
        WebSocket URL of the Rings node RPC interface
        (e.g. ``"ws://localhost:50000"``).
    transport : RingsTransport, optional
        Custom transport.  Defaults to :class:`InMemoryTransport` if ``None``.
    timeout : float
        Default RPC timeout in seconds.
    auto_reconnect : bool
        Whether to attempt reconnection on transport failure.
    """

    def __init__(
        self,
        endpoint: str = "ws://localhost:50000",
        transport: Optional[RingsTransport] = None,
        *,
        timeout: float = DEFAULT_RPC_TIMEOUT,
        auto_reconnect: bool = True,
    ) -> None:
        self._endpoint = endpoint
        self._transport = transport or InMemoryTransport()
        self._timeout = timeout
        self._auto_reconnect = auto_reconnect
        self._state = ConnectionState.DISCONNECTED
        self._local_did: Optional[str] = None
        self._position: int = 0
        self._sub_rings: Dict[str, SubRingInfo] = {}

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def local_did(self) -> Optional[str]:
        """DID of the local node (set after connect)."""
        return self._local_did

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def transport(self) -> RingsTransport:
        """Access the underlying transport (useful in tests)."""
        return self._transport

    # ── Connection lifecycle ──────────────────────────────────────────────

    async def connect(self) -> None:
        """Establish connection to the Rings node."""
        if self._state == ConnectionState.CONNECTED:
            return

        self._state = ConnectionState.CONNECTING
        try:
            await self._transport.connect(self._endpoint)
            # Fetch node info to populate local DID
            info = await self._rpc("node_info", {})
            self._local_did = info.get("did")
            self._position = info.get("position", 0)
            self._state = ConnectionState.CONNECTED
            logger.info("Connected to Rings node at %s (DID: %s)", self._endpoint, self._local_did)
        except Exception as exc:
            self._state = ConnectionState.ERROR
            logger.error("Failed to connect to Rings node: %s", exc)
            raise

    async def disconnect(self) -> None:
        """Gracefully disconnect from the Rings node."""
        if self._state == ConnectionState.DISCONNECTED:
            return
        try:
            await self._transport.disconnect()
        finally:
            self._state = ConnectionState.DISCONNECTED
            logger.info("Disconnected from Rings node")

    # ── DHT operations ────────────────────────────────────────────────────

    async def dht_put(
        self,
        key: str,
        value: Any,
        *,
        operator: DHTOperator = DHTOperator.OVERWRITE,
    ) -> Dict[str, Any]:
        """Store a value in the Chord DHT.

        Parameters
        ----------
        key : str
            Storage key (hashed to a VID position on the ring).
        value : Any
            JSON-serializable value.
        operator : DHTOperator
            How to handle existing values at this key.

        Returns
        -------
        dict
            Confirmation with the key and status.
        """
        return await self._rpc("dht_put", {
            "key": key,
            "value": value,
            "operator": operator.value,
        })

    async def dht_get(self, key: str) -> Any:
        """Retrieve a value from the Chord DHT.

        Parameters
        ----------
        key : str
            The key to look up (O(log N) hops in a real network).

        Returns
        -------
        Any
            The stored value, or ``None`` if not found.
        """
        return await self._rpc("dht_get", {"key": key})

    async def dht_delete(self, key: str) -> Dict[str, Any]:
        """Remove a key from the DHT."""
        return await self._rpc("dht_delete", {"key": key})

    # ── Peer / Ring operations ────────────────────────────────────────────

    async def join_ring(self) -> PeerInfo:
        """Join the Chord ring as a peer.

        Returns
        -------
        PeerInfo
            Information about the local node's position on the ring.
        """
        result = await self._rpc("ring_join", {"did": self._local_did or ""})
        info = PeerInfo(
            did=result.get("did", ""),
            position=result.get("position", 0),
        )
        self._position = info.position
        return info

    async def find_successor(self, identifier: int) -> PeerInfo:
        """Find the successor node for a given identifier on the ring.

        This is the core Chord operation — O(log N) hops.

        Parameters
        ----------
        identifier : int
            A position in Z_{2^160}.

        Returns
        -------
        PeerInfo
            The peer responsible for that position.
        """
        result = await self._rpc("ring_find_successor", {"id": str(identifier)})
        return PeerInfo(did=result.get("did", ""), position=result.get("position", 0))

    async def get_finger_table(self) -> List[FingerEntry]:
        """Retrieve the local node's Chord finger table.

        Returns 160 entries: finger[i].start = (self + 2^i) mod 2^160.
        """
        raw = await self._rpc("ring_finger_table", {})
        return [
            FingerEntry(
                index=entry.get("index", i),
                start=entry.get("start", 0),
                node_did=entry.get("node", ""),
            )
            for i, entry in enumerate(raw)
        ]

    async def get_peers(self) -> List[PeerInfo]:
        """List currently known peers."""
        raw = await self._rpc("ring_peers", {})
        return [
            PeerInfo(
                did=p.get("did", ""),
                position=p.get("position", 0),
                joined_at=p.get("joined_at", 0),
                capabilities=p.get("capabilities", {}),
                reputation=p.get("reputation", 0.0),
            )
            for p in raw
        ]

    # ── Sub-Ring operations ───────────────────────────────────────────────

    async def create_sub_ring(self, topic: str) -> SubRingInfo:
        """Create (or join) a topic-based Sub-Ring.

        Sub-Rings are minimized Chord rings within the main ring. Members
        maintain both main-ring and sub-ring finger tables.

        The VID of the Sub-Ring is ``H(topic)``.
        """
        result = await self._rpc("subring_create", {"topic": topic})
        info = SubRingInfo(
            topic=topic,
            vid=result.get("vid", _compute_vid(topic)),
            member_count=0,
            joined=True,
        )
        self._sub_rings[topic] = info
        return info

    async def join_sub_ring(self, topic: str) -> SubRingInfo:
        """Join an existing Sub-Ring."""
        result = await self._rpc("subring_join", {
            "topic": topic,
            "did": self._local_did or "",
        })
        info = SubRingInfo(
            topic=topic,
            vid=_compute_vid(topic),
            member_count=result.get("member_count", 0),
            joined=True,
        )
        self._sub_rings[topic] = info
        return info

    async def leave_sub_ring(self, topic: str) -> None:
        """Leave a Sub-Ring."""
        await self._rpc("subring_leave", {
            "topic": topic,
            "did": self._local_did or "",
        })
        self._sub_rings.pop(topic, None)

    async def get_sub_ring_members(self, topic: str) -> List[str]:
        """List member DIDs in a Sub-Ring."""
        return await self._rpc("subring_members", {"topic": topic})

    async def broadcast(self, topic: str, message: Any) -> Dict[str, Any]:
        """Broadcast a message to all members of a Sub-Ring.

        Parameters
        ----------
        topic : str
            The Sub-Ring topic.
        message : Any
            JSON-serializable message payload.

        Returns
        -------
        dict
            Delivery report with recipient count.
        """
        return await self._rpc("subring_broadcast", {
            "topic": topic,
            "message": message,
        })

    # ── Session management ────────────────────────────────────────────────

    async def create_session(self, peer_did: str) -> SessionInfo:
        """Create an E2E encrypted session with a peer.

        Uses ElGamal-derived session keys (from the Rings Protocol Layer).
        """
        result = await self._rpc("session_create", {"peer_did": peer_did})
        return SessionInfo(
            session_id=result["session_id"],
            peer_did=peer_did,
        )

    async def session_send(self, session_id: str, data: Any) -> None:
        """Send data over an established session."""
        await self._rpc("session_send", {"session_id": session_id, "data": data})

    async def session_receive(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Receive the latest message from a session (non-blocking)."""
        return await self._rpc("session_receive", {"session_id": session_id})

    async def close_session(self, session_id: str) -> None:
        """Close an E2E session."""
        await self._rpc("session_close", {"session_id": session_id})

    # ── DID resolution ────────────────────────────────────────────────────

    async def resolve_did(self, did: str) -> Optional[Dict[str, Any]]:
        """Resolve a DID to its DID Document via Chord DHT lookup.

        Returns ``None`` if the DID is not found in the network.
        """
        return await self._rpc("did_resolve", {"did": did})

    async def lookup_did(self, did: str) -> Optional[Dict[str, Any]]:
        """Alias for :meth:`resolve_did` (backward compatibility)."""
        return await self._rpc("did_lookup", {"did": did})

    # ── VID helpers ───────────────────────────────────────────────────────

    @staticmethod
    def compute_vid(name: str) -> str:
        """Compute a Virtual DID: ``VID = H(name)``."""
        return _compute_vid(name)

    @staticmethod
    def did_to_position(did: str) -> int:
        """Map a DID to its position on the Chord ring."""
        return _did_to_position(did)

    # ── Convenience: context manager ──────────────────────────────────────

    async def __aenter__(self) -> "RingsClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.disconnect()

    # ── Internal RPC call ─────────────────────────────────────────────────

    async def _rpc(self, method: str, params: Dict[str, Any]) -> Any:
        """Execute an RPC call with timeout and reconnection logic."""
        if not self._transport.is_connected and self._auto_reconnect:
            self._state = ConnectionState.RECONNECTING
            try:
                await self._transport.connect(self._endpoint)
                self._state = ConnectionState.CONNECTED
            except Exception:
                self._state = ConnectionState.ERROR
                raise ConnectionError(
                    f"Rings node unavailable at {self._endpoint}"
                )

        try:
            result = await asyncio.wait_for(
                self._transport.call(method, params),
                timeout=self._timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("RPC timeout: %s (%.1fs)", method, self._timeout)
            raise
        except ConnectionError:
            self._state = ConnectionState.ERROR
            raise
        except Exception as exc:
            logger.error("RPC error [%s]: %s", method, exc)
            raise

    def __repr__(self) -> str:
        return (
            f"RingsClient(endpoint={self._endpoint!r}, "
            f"state={self._state.value}, did={self._local_did!r})"
        )
