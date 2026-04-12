"""
Tests for Rings Network production transports.

Covers WebSocketTransport, HTTPTransport, MultiNodeTransport, and the
create_transport factory — all without requiring live servers (mocked at the
protocol/socket level).
"""

from __future__ import annotations

import asyncio
import json
import logging
import pytest
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from asi_build.rings.transport import (
    HTTPTransport,
    MultiNodeTransport,
    WebSocketTransport,
    create_transport,
)
from asi_build.rings.client import InMemoryTransport, RingsClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers — mock WebSocket connection
# ---------------------------------------------------------------------------

class MockWebSocket:
    """Simulates a websockets.ClientConnection for testing."""

    def __init__(self, responses: Optional[Dict[int, Any]] = None):
        self._responses = responses or {}
        self._sent: List[str] = []
        self._recv_queue: asyncio.Queue[str] = asyncio.Queue()
        self._closed = False
        self._auto_respond = True

    async def send(self, data: str) -> None:
        self._sent.append(data)
        if self._auto_respond:
            msg = json.loads(data)
            req_id = msg.get("id")
            if req_id is not None:
                result = self._responses.get(req_id, {"ok": True})
                resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
                await self._recv_queue.put(json.dumps(resp))

    async def recv(self) -> str:
        if self._closed:
            raise Exception("Connection closed")
        return await self._recv_queue.get()

    async def close(self) -> None:
        self._closed = True
        # Unblock any pending recv
        await self._recv_queue.put('{"close": true}')

    async def ping(self) -> None:
        if self._closed:
            raise Exception("Connection closed")

    def inject_message(self, msg: dict) -> None:
        """Inject a server-push message."""
        self._recv_queue.put_nowait(json.dumps(msg))

    def inject_error(self, req_id: int, message: str = "fail") -> None:
        """Queue an error response."""
        resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -1, "message": message}}
        self._recv_queue.put_nowait(json.dumps(resp))


# ---------------------------------------------------------------------------
# Helpers — mock aiohttp session
# ---------------------------------------------------------------------------

class MockHTTPResponse:
    def __init__(self, body: dict, status: int = 200):
        self._body = body
        self.status = status

    async def json(self) -> dict:
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockHTTPSession:
    def __init__(self, responses: Optional[List[dict]] = None):
        self._responses = list(responses or [{"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}])
        self._call_index = 0
        self.closed = False
        self.post_calls: List[dict] = []

    def post(self, url: str, json: dict = None, **kw) -> MockHTTPResponse:
        self.post_calls.append({"url": url, "json": json})
        idx = min(self._call_index, len(self._responses) - 1)
        self._call_index += 1
        return MockHTTPResponse(self._responses[idx])

    async def close(self) -> None:
        self.closed = True


# ===================================================================
# WebSocketTransport tests
# ===================================================================

class TestWebSocketTransport:
    """WebSocketTransport — 17 tests."""

    def test_create_with_url(self):
        t = WebSocketTransport("ws://localhost:50000/jsonrpc")
        assert t.url == "ws://localhost:50000/jsonrpc"
        assert not t.is_connected
        assert t.stats["messages_sent"] == 0

    def test_repr_disconnected(self):
        t = WebSocketTransport("ws://node:50000")
        r = repr(t)
        assert "ws://node:50000" in r
        assert "disconnected" in r

    @pytest.mark.asyncio
    async def test_connect_disconnect_lifecycle(self):
        t = WebSocketTransport("ws://localhost:50000")
        mock_ws = MockWebSocket()

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect("ws://localhost:50000")
            assert t.is_connected
            # Give tasks a moment to start
            await asyncio.sleep(0.01)

            await t.disconnect()
            assert not t.is_connected

    @pytest.mark.asyncio
    async def test_send_returns_response(self):
        t = WebSocketTransport("ws://localhost:50000")
        mock_ws = MockWebSocket(responses={1: {"key": "test", "value": 42}})

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()
            assert t.is_connected

            result = await t.call("dht_get", {"key": "test"})
            assert result == {"key": "test", "value": 42}

            await t.disconnect()

    @pytest.mark.asyncio
    async def test_jsonrpc_id_correlation(self):
        """Multiple concurrent requests get correctly matched to responses."""
        t = WebSocketTransport("ws://localhost:50000")
        mock_ws = MockWebSocket(responses={
            1: "first",
            2: "second",
            3: "third",
        })

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()

            r1, r2, r3 = await asyncio.gather(
                t.call("method_a", {}),
                t.call("method_b", {}),
                t.call("method_c", {}),
            )

            assert r1 == "first"
            assert r2 == "second"
            assert r3 == "third"

            await t.disconnect()

    @pytest.mark.asyncio
    async def test_request_timeout(self):
        """Requests that aren't answered within timeout raise TimeoutError."""
        t = WebSocketTransport("ws://localhost:50000", request_timeout=0.1)
        mock_ws = MockWebSocket()
        mock_ws._auto_respond = False  # don't send responses

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()

            with pytest.raises(asyncio.TimeoutError):
                await t.call("dht_get", {"key": "slow"})

            assert t.stats["errors"] >= 1
            await t.disconnect()

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        t = WebSocketTransport("ws://localhost:50000")
        mock_ws = MockWebSocket(responses={1: "ok", 2: "ok"})

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()

            await t.call("method_a", {})
            await t.call("method_b", {})

            stats = t.stats
            assert stats["messages_sent"] == 2
            assert stats["messages_received"] == 2

            await t.disconnect()

    @pytest.mark.asyncio
    async def test_error_on_send_when_disconnected(self):
        t = WebSocketTransport("ws://localhost:50000")
        assert not t.is_connected

        with pytest.raises(ConnectionError):
            await t.call("dht_get", {"key": "x"})

    @pytest.mark.asyncio
    async def test_rpc_error_response(self):
        """JSON-RPC error responses are raised as RuntimeError."""
        t = WebSocketTransport("ws://localhost:50000")
        mock_ws = MockWebSocket()
        mock_ws._auto_respond = False

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()

            # Manually inject an error response for request id 1
            async def send_and_inject():
                result = t.call("bad_method", {})
                await asyncio.sleep(0.01)
                mock_ws.inject_error(1, "Method not found")
                return await result

            with pytest.raises(RuntimeError, match="Method not found"):
                await send_and_inject()

            await t.disconnect()

    @pytest.mark.asyncio
    async def test_unsolicited_event_queued(self):
        """Messages without matching request id go to the event queue."""
        t = WebSocketTransport("ws://localhost:50000")
        mock_ws = MockWebSocket()

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()
            await asyncio.sleep(0.01)

            # Inject an unsolicited event
            mock_ws.inject_message({"method": "broadcast", "params": {"topic": "test", "data": "hello"}})

            event = await asyncio.wait_for(t.receive_event(), timeout=1.0)
            assert event["method"] == "broadcast"
            assert event["params"]["data"] == "hello"

            await t.disconnect()

    @pytest.mark.asyncio
    async def test_concurrent_requests_no_interference(self):
        """Multiple concurrent requests don't interfere with each other."""
        t = WebSocketTransport("ws://localhost:50000")
        responses = {i: f"result_{i}" for i in range(1, 11)}
        mock_ws = MockWebSocket(responses=responses)

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()

            tasks = [t.call(f"method_{i}", {"i": i}) for i in range(1, 11)]
            results = await asyncio.gather(*tasks)

            assert results == [f"result_{i}" for i in range(1, 11)]
            assert t.stats["messages_sent"] == 10

            await t.disconnect()

    @pytest.mark.asyncio
    async def test_connection_state_tracking(self):
        t = WebSocketTransport("ws://localhost:50000")
        assert not t.is_connected

        mock_ws = MockWebSocket()
        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()
            assert t.is_connected

            await t.disconnect()
            assert not t.is_connected

    @pytest.mark.asyncio
    async def test_connect_failure_raises(self):
        """Connection failure raises ConnectionError."""
        t = WebSocketTransport("ws://bad:50000", max_reconnect_attempts=1)

        async def fail_connect(*a, **kw):
            raise OSError("Connection refused")

        with patch("websockets.connect", side_effect=fail_connect):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await t.connect()
            assert not t.is_connected

    @pytest.mark.asyncio
    async def test_disconnect_cancels_pending(self):
        """Pending futures are cancelled on disconnect."""
        t = WebSocketTransport("ws://localhost:50000", request_timeout=5.0)
        mock_ws = MockWebSocket()
        mock_ws._auto_respond = False

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()

            # Start a request that won't be answered
            task = asyncio.ensure_future(t.call("slow_method", {}))
            await asyncio.sleep(0.01)

            assert t.pending_count >= 1
            await t.disconnect()

            # The task should fail with ConnectionError
            with pytest.raises((ConnectionError, asyncio.CancelledError)):
                await task

    @pytest.mark.asyncio
    async def test_repr_when_connected(self):
        t = WebSocketTransport("ws://node:8080")
        mock_ws = MockWebSocket()

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()
            r = repr(t)
            assert "connected" in r
            assert "ws://node:8080" in r
            await t.disconnect()

    @pytest.mark.asyncio
    async def test_jsonrpc_payload_format(self):
        """Verify the exact JSON-RPC 2.0 format sent over the wire."""
        t = WebSocketTransport("ws://localhost:50000")
        mock_ws = MockWebSocket(responses={1: "ok"})

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()
            await t.call("dht_put", {"key": "k", "value": "v"})

            sent = json.loads(mock_ws._sent[0])
            assert sent["jsonrpc"] == "2.0"
            assert sent["id"] == 1
            assert sent["method"] == "dht_put"
            assert sent["params"] == {"key": "k", "value": "v"}

            await t.disconnect()

    @pytest.mark.asyncio
    async def test_heartbeat_sends_ping(self):
        """Heartbeat task sends pings at the configured interval."""
        t = WebSocketTransport(
            "ws://localhost:50000",
            heartbeat_interval=0.05,  # very short for testing
        )
        mock_ws = MockWebSocket()
        ping_count = 0
        original_ping = mock_ws.ping

        async def counting_ping():
            nonlocal ping_count
            ping_count += 1
            await original_ping()

        mock_ws.ping = counting_ping

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()
            await asyncio.sleep(0.15)  # ~3 heartbeats
            assert ping_count >= 2
            await t.disconnect()


# ===================================================================
# HTTPTransport tests
# ===================================================================

class TestHTTPTransport:
    """HTTPTransport — 10 tests."""

    def test_create_with_url(self):
        t = HTTPTransport("http://rings-node:50000")
        assert t.url == "http://rings-node:50000"
        assert not t.is_connected

    def test_url_trailing_slash_stripped(self):
        t = HTTPTransport("http://rings-node:50000/")
        assert t.url == "http://rings-node:50000"

    def test_repr(self):
        t = HTTPTransport("http://node:8080")
        r = repr(t)
        assert "http://node:8080" in r
        assert "disconnected" in r

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        t = HTTPTransport("http://node:50000")

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session_cls.return_value = MockHTTPSession()
            await t.connect()
            assert t.is_connected

            await t.disconnect()
            assert not t.is_connected

    @pytest.mark.asyncio
    async def test_send_makes_post_request(self):
        t = HTTPTransport("http://node:50000")
        mock_session = MockHTTPSession([
            {"jsonrpc": "2.0", "id": 1, "result": {"value": 42}}
        ])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await t.connect()

            result = await t.call("dht_get", {"key": "test"})
            assert result == {"value": 42}

            assert len(mock_session.post_calls) == 1
            call = mock_session.post_calls[0]
            assert call["url"] == "http://node:50000"
            payload = call["json"]
            assert payload["jsonrpc"] == "2.0"
            assert payload["method"] == "dht_get"
            assert payload["params"] == {"key": "test"}

            await t.disconnect()

    @pytest.mark.asyncio
    async def test_error_response(self):
        t = HTTPTransport("http://node:50000")
        mock_session = MockHTTPSession([
            {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}
        ])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await t.connect()

            with pytest.raises(RuntimeError, match="Method not found"):
                await t.call("bad_method", {})

            assert t.stats["errors"] == 1
            await t.disconnect()

    @pytest.mark.asyncio
    async def test_send_when_disconnected(self):
        t = HTTPTransport("http://node:50000")
        with pytest.raises(ConnectionError):
            await t.call("dht_get", {"key": "x"})

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        t = HTTPTransport("http://node:50000")
        mock_session = MockHTTPSession([
            {"jsonrpc": "2.0", "id": 1, "result": "a"},
            {"jsonrpc": "2.0", "id": 2, "result": "b"},
        ])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await t.connect()
            await t.call("m1", {})
            await t.call("m2", {})
            assert t.stats["requests"] == 2
            assert t.stats["errors"] == 0
            await t.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_calls_increment_id(self):
        t = HTTPTransport("http://node:50000")
        mock_session = MockHTTPSession([
            {"jsonrpc": "2.0", "id": 1, "result": "a"},
            {"jsonrpc": "2.0", "id": 2, "result": "b"},
        ])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await t.connect()
            await t.call("m1", {})
            await t.call("m2", {})

            ids = [c["json"]["id"] for c in mock_session.post_calls]
            assert ids == [1, 2]
            await t.disconnect()

    @pytest.mark.asyncio
    async def test_session_closed_on_disconnect(self):
        t = HTTPTransport("http://node:50000")
        mock_session = MockHTTPSession()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await t.connect()
            await t.disconnect()
            assert mock_session.closed


# ===================================================================
# MultiNodeTransport tests
# ===================================================================

class TestMultiNodeTransport:
    """MultiNodeTransport — 12 tests."""

    def test_create_with_urls(self):
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])
        assert len(t._urls) == 2
        assert not t.is_connected

    def test_empty_urls_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            MultiNodeTransport([])

    def test_repr(self):
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])
        r = repr(t)
        assert "nodes=2" in r
        assert "connected=0" in r

    @pytest.mark.asyncio
    async def test_connect_all_nodes(self):
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])

        mock_ws1 = MockWebSocket()
        mock_ws2 = MockWebSocket()
        call_count = 0

        async def mock_connect(*a, **kw):
            nonlocal call_count
            call_count += 1
            return mock_ws1 if call_count <= 1 else mock_ws2

        with patch("websockets.connect", side_effect=mock_connect):
            await t.connect()
            assert t.is_connected
            assert t.connected_count == 2
            await t.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_all_nodes(self):
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])

        mock_ws = MockWebSocket()
        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            await t.connect()
            await t.disconnect()
            assert not t.is_connected
            assert t.connected_count == 0

    @pytest.mark.asyncio
    async def test_round_robin_distribution(self):
        """Requests are distributed round-robin across nodes."""
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])

        # Create two mock transports manually
        t1 = _MockTransportForMulti("n1")
        t2 = _MockTransportForMulti("n2")
        t._transports = [t1, t2]
        t._connected = True

        await t.call("method_a", {})
        await t.call("method_b", {})
        await t.call("method_c", {})

        # Should round-robin: n1, n2, n1
        assert t1.call_count == 2
        assert t2.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """When one node fails, the next healthy node handles the request."""
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])

        t1 = _MockTransportForMulti("n1", fail=True)
        t2 = _MockTransportForMulti("n2")
        t._transports = [t1, t2]
        t._connected = True

        result = await t.call("test_method", {})
        assert result["node"] == "n2"

    @pytest.mark.asyncio
    async def test_all_nodes_failed_raises(self):
        """When all nodes fail, ConnectionError is raised."""
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])

        t1 = _MockTransportForMulti("n1", fail=True)
        t2 = _MockTransportForMulti("n2", fail=True)
        t._transports = [t1, t2]
        t._connected = True

        with pytest.raises(ConnectionError, match="All 2 nodes failed"):
            await t.call("test_method", {})

    @pytest.mark.asyncio
    async def test_connected_count_accurate(self):
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000", "ws://n3:50000"])

        t1 = _MockTransportForMulti("n1")
        t2 = _MockTransportForMulti("n2", connected=False)
        t3 = _MockTransportForMulti("n3")
        t._transports = [t1, t2, t3]
        t._connected = True

        assert t.connected_count == 2

    @pytest.mark.asyncio
    async def test_single_node_failure_doesnt_break(self):
        """System works even when one node is down."""
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])

        t1 = _MockTransportForMulti("n1", connected=False)
        t2 = _MockTransportForMulti("n2")
        t._transports = [t1, t2]
        t._connected = True

        result = await t.call("test_method", {})
        assert result["node"] == "n2"

    @pytest.mark.asyncio
    async def test_stats_aggregated(self):
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])

        t1 = _MockTransportForMulti("n1")
        t1._stats = {"messages_sent": 5, "errors": 1}
        t2 = _MockTransportForMulti("n2")
        t2._stats = {"messages_sent": 3, "errors": 0}
        t._transports = [t1, t2]
        t._connected = True

        stats = t.stats
        assert stats["messages_sent"] == 8
        assert stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_recovery_when_node_comes_back(self):
        """A node that was down can start serving after recovery."""
        t = MultiNodeTransport(["ws://n1:50000", "ws://n2:50000"])

        t1 = _MockTransportForMulti("n1", connected=False)
        t2 = _MockTransportForMulti("n2")
        t._transports = [t1, t2]
        t._connected = True

        # Initially only n2 serves
        result = await t.call("test_method", {})
        assert result["node"] == "n2"

        # n1 recovers
        t1._connected = True
        t1._fail = False

        # Reset round-robin to start from t1
        t._current_index = 0
        result = await t.call("test_method", {})
        assert result["node"] == "n1"


# ===================================================================
# create_transport factory tests
# ===================================================================

class TestCreateTransport:
    """create_transport factory — 6 tests."""

    def test_ws_creates_websocket(self):
        t = create_transport("ws://node:50000/jsonrpc")
        assert isinstance(t, WebSocketTransport)
        assert t.url == "ws://node:50000/jsonrpc"

    def test_wss_creates_websocket(self):
        t = create_transport("wss://node:50000/jsonrpc")
        assert isinstance(t, WebSocketTransport)

    def test_http_creates_http(self):
        t = create_transport("http://node:50000")
        assert isinstance(t, HTTPTransport)
        assert t.url == "http://node:50000"

    def test_https_creates_http(self):
        t = create_transport("https://node:50000")
        assert isinstance(t, HTTPTransport)

    def test_memory_creates_in_memory(self):
        t = create_transport("memory://")
        assert isinstance(t, InMemoryTransport)

    def test_comma_separated_creates_multi(self):
        t = create_transport("ws://n1:50000,ws://n2:50000")
        assert isinstance(t, MultiNodeTransport)
        assert len(t._urls) == 2

    def test_unknown_scheme_raises(self):
        with pytest.raises(ValueError, match="Unknown URL scheme"):
            create_transport("ftp://node:50000")


# ===================================================================
# RingsClient.from_url integration tests
# ===================================================================

class TestRingsClientFromUrl:
    """RingsClient.from_url — 5 tests."""

    @pytest.mark.asyncio
    async def test_from_url_memory(self):
        """memory:// creates an InMemoryTransport and connects."""
        client = await RingsClient.from_url("memory://")
        assert client.is_connected
        assert isinstance(client.transport, InMemoryTransport)
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_from_url_ws(self):
        """ws:// creates a WebSocketTransport."""
        mock_ws = MockWebSocket(responses={
            1: {"did": "did:rings:test", "position": 0, "version": "0.1.0", "uptime": 0, "peer_count": 0}
        })

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            client = await RingsClient.from_url("ws://node:50000")
            assert client.is_connected
            assert isinstance(client.transport, WebSocketTransport)
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_from_url_http(self):
        """http:// creates an HTTPTransport."""
        mock_session = MockHTTPSession([
            {"jsonrpc": "2.0", "id": 1, "result": {
                "did": "did:rings:test", "position": 0, "version": "0.1.0",
                "uptime": 0, "peer_count": 0,
            }}
        ])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            client = await RingsClient.from_url("http://node:50000")
            assert client.is_connected
            assert isinstance(client.transport, HTTPTransport)
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_from_url_dht_roundtrip(self):
        """End-to-end: from_url with memory:// → DHT put/get."""
        client = await RingsClient.from_url("memory://")
        await client.dht_put("key1", {"hello": "world"})
        val = await client.dht_get("key1")
        assert val == {"hello": "world"}
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_from_url_kwargs_forwarded(self):
        """Transport kwargs are forwarded to the transport constructor."""
        mock_ws = MockWebSocket(responses={
            1: {"did": "did:rings:test", "position": 0, "version": "0.1.0", "uptime": 0, "peer_count": 0}
        })

        with patch("websockets.connect", new_callable=lambda: _async_factory(mock_ws)):
            client = await RingsClient.from_url(
                "ws://node:50000",
                request_timeout=42.0,
                heartbeat_interval=99.0,
            )
            assert isinstance(client.transport, WebSocketTransport)
            # Check the kwargs were applied
            assert client.transport._request_timeout == 42.0
            assert client.transport._heartbeat_interval == 99.0
            await client.disconnect()


# ===================================================================
# Helpers
# ===================================================================

class _MockTransportForMulti:
    """Minimal mock transport for MultiNodeTransport tests."""

    def __init__(self, name: str, *, fail: bool = False, connected: bool = True):
        self._name = name
        self._fail = fail
        self._connected = connected
        self.call_count = 0
        self._stats: Dict[str, int] = {"messages_sent": 0, "errors": 0}

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    async def connect(self, endpoint: str = "") -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def call(self, method: str, params: Dict[str, Any]) -> Any:
        if self._fail:
            raise ConnectionError(f"Node {self._name} is down")
        self.call_count += 1
        return {"ok": True, "node": self._name}


def _async_factory(mock_ws: MockWebSocket):
    """Create an AsyncMock class that returns mock_ws when awaited.
    
    Works with ``patch("websockets.connect", new_callable=...)``."""
    class _Factory:
        def __init__(self, *a, **kw):
            pass
        def __call__(self, *args, **kwargs):
            return self
        def __await__(self):
            async def _ret():
                return mock_ws
            return _ret().__await__()
    return _Factory
