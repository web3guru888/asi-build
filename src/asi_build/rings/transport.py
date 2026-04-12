"""
Rings Network Transport Implementations
========================================

Production transports for connecting a :class:`~.client.RingsClient` to real
Rings network nodes.  Three transports are provided:

:class:`WebSocketTransport`
    Persistent WebSocket connection with JSON-RPC framing, automatic
    reconnection, heartbeat, and request-response correlation.

:class:`HTTPTransport`
    Stateless HTTP/JSON-RPC transport via ``aiohttp``.  Suitable when
    persistent connections are not needed.

:class:`MultiNodeTransport`
    Load-balanced wrapper around multiple transports — round-robin
    routing with automatic fallback on failure.

All three satisfy the :class:`~.client.RingsTransport` ``Protocol``.

Factory
~~~~~~~

Use :func:`create_transport` to build a transport from a URL string::

    transport = create_transport("ws://rings-node:50000/jsonrpc")
    transport = create_transport("http://rings-node:50000")
    transport = create_transport("ws://n1:50000,ws://n2:50000")
    transport = create_transport("memory://")       # testing
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WebSocket Transport
# ---------------------------------------------------------------------------


class WebSocketTransport:
    """Production WebSocket transport for Rings network nodes.

    Connects to a Rings node's WebSocket RPC endpoint and translates
    :class:`~.client.RingsClient` operations into JSON-RPC 2.0 messages.

    Features
    --------
    - Auto-reconnection with exponential backoff
    - Heartbeat / keepalive (WebSocket pings)
    - Request-response correlation via JSON-RPC ``id`` tracking
    - Unsolicited message queue for server-push events
    - Graceful shutdown with task cleanup

    Parameters
    ----------
    node_url : str
        WebSocket endpoint, e.g. ``"ws://rings-node:50000/jsonrpc"``.
    reconnect_interval : float
        Initial delay (seconds) before a reconnection attempt.
    max_reconnect_delay : float
        Cap for the exponential-backoff delay.
    heartbeat_interval : float
        Seconds between WebSocket-level pings.
    request_timeout : float
        Default per-request timeout.
    max_reconnect_attempts : int
        How many consecutive reconnection attempts before giving up (0 = unlimited).
    """

    def __init__(
        self,
        node_url: str,
        *,
        reconnect_interval: float = 2.0,
        max_reconnect_delay: float = 60.0,
        heartbeat_interval: float = 30.0,
        request_timeout: float = 10.0,
        max_reconnect_attempts: int = 0,
    ) -> None:
        self._url = node_url
        self._reconnect_interval = reconnect_interval
        self._max_reconnect_delay = max_reconnect_delay
        self._heartbeat_interval = heartbeat_interval
        self._request_timeout = request_timeout
        self._max_reconnect_attempts = max_reconnect_attempts

        self._ws: Any = None  # websockets.ClientConnection
        self._connected = False
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future[Any]] = {}
        self._event_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._receive_task: Optional[asyncio.Task[None]] = None
        self._heartbeat_task: Optional[asyncio.Task[None]] = None
        self._reconnect_attempts = 0
        self._endpoint: str = ""  # set in connect()
        self._shutting_down = False
        self._stats: Dict[str, int] = {
            "messages_sent": 0,
            "messages_received": 0,
            "reconnects": 0,
            "errors": 0,
        }

    # ── RingsTransport Protocol conformance ───────────────────────────────

    async def connect(self, endpoint: str = "") -> None:
        """Establish the WebSocket connection.

        Parameters
        ----------
        endpoint : str
            If given, overrides the URL supplied at construction time.
        """
        if endpoint:
            self._endpoint = endpoint
        elif not self._endpoint:
            self._endpoint = self._url

        self._shutting_down = False
        await self._do_connect()

    async def disconnect(self) -> None:
        """Gracefully close the connection and cancel background tasks."""
        self._shutting_down = True
        await self._cleanup_tasks()

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        self._connected = False

        # Cancel all pending futures
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(ConnectionError("Transport disconnected"))
        self._pending.clear()

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def call(self, method: str, params: Dict[str, Any]) -> Any:
        """Send a JSON-RPC 2.0 request and wait for the correlated response.

        Raises
        ------
        ConnectionError
            If not connected and reconnection fails.
        asyncio.TimeoutError
            If the response doesn't arrive within *request_timeout*.
        RuntimeError
            If the RPC returns an error object.
        """
        if not self._connected:
            raise ConnectionError("WebSocketTransport is not connected")

        self._request_id += 1
        req_id = self._request_id

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }

        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending[req_id] = future

        try:
            raw = json.dumps(payload)
            await self._ws.send(raw)
            self._stats["messages_sent"] += 1

            result = await asyncio.wait_for(future, timeout=self._request_timeout)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            self._stats["errors"] += 1
            raise
        except Exception:
            self._pending.pop(req_id, None)
            self._stats["errors"] += 1
            raise

    # ── Public helpers ────────────────────────────────────────────────────

    async def receive_event(self) -> dict:
        """Block until an unsolicited server-push event is available."""
        return await self._event_queue.get()

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    @property
    def url(self) -> str:
        return self._url

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    # ── Internals ─────────────────────────────────────────────────────────

    async def _do_connect(self) -> None:
        """Low-level connect — imports websockets lazily."""
        import websockets  # noqa: F811

        try:
            self._ws = await websockets.connect(
                self._endpoint or self._url,
                open_timeout=self._request_timeout,
                ping_interval=None,  # we run our own heartbeat
                close_timeout=5,
            )
            self._connected = True
            self._reconnect_attempts = 0

            # Kick off background tasks
            self._receive_task = asyncio.ensure_future(self._receive_loop())
            self._heartbeat_task = asyncio.ensure_future(self._heartbeat_loop())

            logger.info("WebSocket connected to %s", self._endpoint or self._url)
        except Exception as exc:
            self._connected = False
            self._stats["errors"] += 1
            logger.error("WebSocket connection failed: %s", exc)
            raise ConnectionError(f"Failed to connect to {self._endpoint or self._url}: {exc}") from exc

    async def _receive_loop(self) -> None:
        """Read messages from the WebSocket, dispatch responses / queue events."""
        try:
            while self._connected and self._ws is not None:
                try:
                    raw = await self._ws.recv()
                except Exception:
                    if self._shutting_down:
                        return
                    self._connected = False
                    self._stats["errors"] += 1
                    await self._try_reconnect()
                    return

                self._stats["messages_received"] += 1

                try:
                    msg = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    logger.warning("Non-JSON message received, dropping")
                    continue

                # Route JSON-RPC responses to pending futures
                msg_id = msg.get("id")
                if msg_id is not None and msg_id in self._pending:
                    future = self._pending.pop(msg_id)
                    if not future.done():
                        if "error" in msg:
                            future.set_exception(
                                RuntimeError(
                                    f"RPC error: {msg['error'].get('message', msg['error'])}"
                                )
                            )
                        else:
                            future.set_result(msg.get("result"))
                else:
                    # Unsolicited event
                    await self._event_queue.put(msg)
        except asyncio.CancelledError:
            pass

    async def _heartbeat_loop(self) -> None:
        """Send periodic WebSocket pings."""
        try:
            while self._connected and self._ws is not None:
                await asyncio.sleep(self._heartbeat_interval)
                if self._ws is not None and self._connected:
                    try:
                        await self._ws.ping()
                    except Exception:
                        if not self._shutting_down:
                            self._stats["errors"] += 1
                            logger.warning("Heartbeat ping failed")
        except asyncio.CancelledError:
            pass

    async def _try_reconnect(self) -> None:
        """Attempt reconnection with exponential backoff."""
        if self._shutting_down:
            return

        while not self._shutting_down:
            self._reconnect_attempts += 1
            if (
                self._max_reconnect_attempts > 0
                and self._reconnect_attempts > self._max_reconnect_attempts
            ):
                logger.error(
                    "Max reconnection attempts (%d) reached",
                    self._max_reconnect_attempts,
                )
                return

            delay = min(
                self._reconnect_interval * (2 ** (self._reconnect_attempts - 1)),
                self._max_reconnect_delay,
            )
            logger.info(
                "Reconnecting in %.1fs (attempt %d)…",
                delay,
                self._reconnect_attempts,
            )
            await asyncio.sleep(delay)

            try:
                await self._cleanup_tasks()
                await self._do_connect()
                self._stats["reconnects"] += 1
                return
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("Reconnection attempt %d failed: %s", self._reconnect_attempts, exc)

    async def _cleanup_tasks(self) -> None:
        """Cancel background tasks."""
        for task in (self._receive_task, self._heartbeat_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        self._receive_task = None
        self._heartbeat_task = None

    def __repr__(self) -> str:
        state = "connected" if self._connected else "disconnected"
        return f"WebSocketTransport(url={self._url!r}, state={state})"


# ---------------------------------------------------------------------------
# HTTP Transport
# ---------------------------------------------------------------------------


class HTTPTransport:
    """HTTP/REST transport for Rings nodes exposing an HTTP JSON-RPC API.

    Simpler stateless alternative to :class:`WebSocketTransport` when
    persistent connections or server-push are not required.

    Parameters
    ----------
    node_url : str
        HTTP endpoint, e.g. ``"http://rings-node:50000"``.
    request_timeout : float
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        node_url: str,
        *,
        request_timeout: float = 10.0,
    ) -> None:
        self._url = node_url.rstrip("/")
        self._request_timeout = request_timeout
        self._session: Any = None  # aiohttp.ClientSession
        self._connected = False
        self._request_id = 0
        self._endpoint: str = ""
        self._stats: Dict[str, int] = {"requests": 0, "errors": 0}

    # ── RingsTransport Protocol conformance ───────────────────────────────

    async def connect(self, endpoint: str = "") -> None:
        """Create the HTTP session."""
        import aiohttp

        if endpoint:
            self._endpoint = endpoint
        elif not self._endpoint:
            self._endpoint = self._url

        timeout = aiohttp.ClientTimeout(total=self._request_timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self._connected = True
        logger.info("HTTP transport ready for %s", self._endpoint or self._url)

    async def disconnect(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            await self._session.close()
            self._session = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def call(self, method: str, params: Dict[str, Any]) -> Any:
        """Send a JSON-RPC 2.0 POST request.

        Raises
        ------
        ConnectionError
            If the session is not open.
        RuntimeError
            If the RPC returns an error object.
        """
        if not self._connected or self._session is None:
            raise ConnectionError("HTTPTransport is not connected")

        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        url = self._endpoint or self._url
        self._stats["requests"] += 1

        try:
            async with self._session.post(url, json=payload) as resp:
                body = await resp.json()
                if "error" in body:
                    self._stats["errors"] += 1
                    err = body["error"]
                    raise RuntimeError(
                        f"RPC error: {err.get('message', err)}"
                    )
                return body.get("result")
        except RuntimeError:
            raise
        except Exception as exc:
            self._stats["errors"] += 1
            raise ConnectionError(f"HTTP request failed: {exc}") from exc

    # ── Public helpers ────────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    @property
    def url(self) -> str:
        return self._url

    def __repr__(self) -> str:
        state = "connected" if self._connected else "disconnected"
        return f"HTTPTransport(url={self._url!r}, state={state})"


# ---------------------------------------------------------------------------
# Multi-Node Transport
# ---------------------------------------------------------------------------


class MultiNodeTransport:
    """Load-balanced transport across multiple Rings nodes.

    Maintains independent transports for each node.  Requests are routed
    round-robin; on failure the next healthy node is tried.

    Parameters
    ----------
    node_urls : list[str]
        URLs for each node (all must use the same scheme).
    transport_type : str
        ``"websocket"`` or ``"http"``.
    kwargs
        Forwarded to the per-node transport constructor.
    """

    def __init__(
        self,
        node_urls: List[str],
        transport_type: str = "websocket",
        **kwargs: Any,
    ) -> None:
        if not node_urls:
            raise ValueError("At least one node URL is required")
        self._urls = node_urls
        self._transport_type = transport_type
        self._kwargs = kwargs
        self._transports: List[Union[WebSocketTransport, HTTPTransport]] = []
        self._current_index = 0
        self._connected = False
        self._endpoint: str = ""

    # ── RingsTransport Protocol conformance ───────────────────────────────

    async def connect(self, endpoint: str = "") -> None:
        """Connect to all nodes.  Failures on individual nodes are logged
        but do not prevent the transport from becoming available if at least
        one node connects."""
        if endpoint:
            self._endpoint = endpoint

        self._transports = []
        for url in self._urls:
            t = _make_single_transport(url, self._transport_type, **self._kwargs)
            try:
                await t.connect(url)
            except Exception as exc:
                logger.warning("Could not connect to %s: %s", url, exc)
            self._transports.append(t)

        if self.connected_count == 0:
            raise ConnectionError("Failed to connect to any node")

        self._connected = True
        logger.info(
            "MultiNodeTransport: %d/%d nodes connected",
            self.connected_count,
            len(self._urls),
        )

    async def disconnect(self) -> None:
        """Disconnect from all nodes."""
        for t in self._transports:
            try:
                await t.disconnect()
            except Exception:
                pass
        self._transports.clear()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.connected_count > 0

    async def call(self, method: str, params: Dict[str, Any]) -> Any:
        """Route to the next healthy transport (round-robin + fallback)."""
        if not self._transports:
            raise ConnectionError("No transports available")

        start = self._current_index
        tried = 0
        last_exc: Optional[Exception] = None
        n = len(self._transports)

        while tried < n:
            idx = (start + tried) % n
            transport = self._transports[idx]
            if transport.is_connected:
                try:
                    result = await transport.call(method, params)
                    self._current_index = (idx + 1) % n
                    return result
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "Node %d (%s) failed: %s — trying next",
                        idx,
                        self._urls[idx],
                        exc,
                    )
            tried += 1

        raise ConnectionError(
            f"All {n} nodes failed. Last error: {last_exc}"
        )

    # ── Public helpers ────────────────────────────────────────────────────

    @property
    def connected_count(self) -> int:
        """Number of currently connected nodes."""
        return sum(1 for t in self._transports if t.is_connected)

    @property
    def stats(self) -> Dict[str, Any]:
        """Aggregated stats from all nodes."""
        agg: Dict[str, int] = {}
        for t in self._transports:
            for k, v in t.stats.items():
                agg[k] = agg.get(k, 0) + v
        return agg

    @property
    def transports(self) -> List[Union[WebSocketTransport, HTTPTransport]]:
        return list(self._transports)

    def __repr__(self) -> str:
        return (
            f"MultiNodeTransport(nodes={len(self._urls)}, "
            f"connected={self.connected_count})"
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _make_single_transport(
    url: str, transport_type: str = "", **kwargs: Any
) -> Union[WebSocketTransport, HTTPTransport]:
    """Create a single transport from a URL, auto-detecting scheme."""
    if transport_type == "http" or url.startswith("http://") or url.startswith("https://"):
        return HTTPTransport(url, **{k: v for k, v in kwargs.items() if k == "request_timeout"})
    # Default to WebSocket
    return WebSocketTransport(url, **kwargs)


def create_transport(
    url: str, **kwargs: Any
) -> Union[WebSocketTransport, HTTPTransport, MultiNodeTransport, Any]:
    """Factory: build the appropriate transport from a connection string.

    Schemes
    -------
    ``ws://``, ``wss://``
        → :class:`WebSocketTransport`
    ``http://``, ``https://``
        → :class:`HTTPTransport`
    ``memory://``
        → :class:`~.client.InMemoryTransport` (for testing)
    Comma-separated URLs
        → :class:`MultiNodeTransport`

    Examples
    --------
    >>> create_transport("ws://rings-node:50000/jsonrpc")
    WebSocketTransport(url='ws://rings-node:50000/jsonrpc', state=disconnected)
    >>> create_transport("http://rings-node:50000")
    HTTPTransport(url='http://rings-node:50000', state=disconnected)
    >>> create_transport("ws://n1:50000,ws://n2:50000")
    MultiNodeTransport(nodes=2, connected=0)
    """
    # Multiple URLs → MultiNodeTransport
    if "," in url:
        urls = [u.strip() for u in url.split(",") if u.strip()]
        return MultiNodeTransport(urls, **kwargs)

    # memory:// → InMemoryTransport
    if url.startswith("memory://"):
        from .client import InMemoryTransport

        return InMemoryTransport()

    # http(s):// → HTTPTransport
    if url.startswith("http://") or url.startswith("https://"):
        return HTTPTransport(url, **{k: v for k, v in kwargs.items() if k == "request_timeout"})

    # ws(s):// → WebSocketTransport
    if url.startswith("ws://") or url.startswith("wss://"):
        return WebSocketTransport(url, **kwargs)

    raise ValueError(
        f"Unknown URL scheme in {url!r}. "
        "Supported: ws://, wss://, http://, https://, memory://"
    )
