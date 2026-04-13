"""TemporalGraph protocol and implementations.

* :class:`TemporalGraph` — runtime-checkable protocol
* :class:`DictTemporalGraph` — async, lock-protected, DAG-enforced
* :class:`NullTemporalGraph` — no-op sentinel
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Protocol, Sequence, runtime_checkable

from .types import TemporalEdge, TemporalGraphConfig, TemporalNode


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class TemporalGraph(Protocol):
    """Minimal contract consumed by EventSequencer / PredictiveEngine."""

    async def add_node(self, node: TemporalNode) -> None: ...
    async def add_edge(self, edge: TemporalEdge) -> None: ...
    async def get_successors(self, node_id: str) -> Sequence[TemporalNode]: ...
    async def get_predecessors(self, node_id: str) -> Sequence[TemporalNode]: ...
    async def check_consistency(self) -> bool: ...
    async def prune(self, horizon_ns: int) -> int: ...
    def stats(self) -> dict[str, int]: ...


# ---------------------------------------------------------------------------
# Primary implementation
# ---------------------------------------------------------------------------

class DictTemporalGraph:
    """In-memory directed acyclic graph with Allen interval relations.

    All mutating operations are serialised behind an :class:`asyncio.Lock`
    so the graph is safe to share across concurrent coroutines within a
    single event-loop.
    """

    def __init__(
        self, config: TemporalGraphConfig = TemporalGraphConfig()
    ) -> None:
        self._config = config
        self._lock = asyncio.Lock()

        self._nodes: dict[str, TemporalNode] = {}
        self._edges: list[TemporalEdge] = []
        self._successors: dict[str, list[str]] = defaultdict(list)
        self._predecessors: dict[str, list[str]] = defaultdict(list)
        self._insertion_order: deque[str] = deque()

        # Counters
        self._nodes_added = 0
        self._edges_added = 0
        self._cycle_rejections = 0
        self._prune_count = 0

    # -- nodes --------------------------------------------------------------

    async def add_node(self, node: TemporalNode) -> None:
        async with self._lock:
            if node.node_id in self._nodes:
                return  # duplicate — silently ignored
            # Evict oldest when at capacity
            if len(self._nodes) >= self._config.max_nodes:
                oldest = self._insertion_order.popleft()
                self._nodes.pop(oldest, None)
            self._nodes[node.node_id] = node
            self._insertion_order.append(node.node_id)
            self._nodes_added += 1

    # -- edges --------------------------------------------------------------

    async def add_edge(self, edge: TemporalEdge) -> None:
        async with self._lock:
            if edge.from_id not in self._nodes or edge.to_id not in self._nodes:
                raise KeyError(
                    f"Unknown node(s): {edge.from_id!r}, {edge.to_id!r}"
                )
            if self._config.consistency_check:
                # Temporarily add the forward link and test for a cycle.
                self._successors[edge.from_id].append(edge.to_id)
                if self._has_cycle(edge.from_id):
                    self._successors[edge.from_id].remove(edge.to_id)
                    self._cycle_rejections += 1
                    raise ValueError("Edge would create a cycle")
                # Edge is safe — record the reverse link and persist.
                self._predecessors[edge.to_id].append(edge.from_id)
            else:
                self._successors[edge.from_id].append(edge.to_id)
                self._predecessors[edge.to_id].append(edge.from_id)

            self._edges.append(edge)
            self._edges_added += 1

    # -- queries ------------------------------------------------------------

    async def get_successors(self, node_id: str) -> Sequence[TemporalNode]:
        async with self._lock:
            return [
                self._nodes[nid]
                for nid in self._successors.get(node_id, [])
                if nid in self._nodes
            ]

    async def get_predecessors(self, node_id: str) -> Sequence[TemporalNode]:
        async with self._lock:
            return [
                self._nodes[nid]
                for nid in self._predecessors.get(node_id, [])
                if nid in self._nodes
            ]

    async def check_consistency(self) -> bool:
        """Return ``True`` if the graph is a valid DAG (no cycles)."""
        async with self._lock:
            visited: set[str] = set()
            in_stack: set[str] = set()

            def dfs(node: str) -> bool:
                visited.add(node)
                in_stack.add(node)
                for nxt in self._successors.get(node, []):
                    if nxt not in visited:
                        if dfs(nxt):
                            return True
                    elif nxt in in_stack:
                        return True
                in_stack.discard(node)
                return False

            for nid in list(self._nodes):
                if nid not in visited:
                    if dfs(nid):
                        return False
            return True

    # -- maintenance --------------------------------------------------------

    async def prune(self, horizon_ns: int) -> int:
        """Remove nodes whose ``timestamp_ns`` is strictly less than *horizon_ns*.

        Returns the number of nodes removed.
        """
        async with self._lock:
            stale = {
                nid
                for nid, n in self._nodes.items()
                if n.timestamp_ns < horizon_ns
            }
            for nid in stale:
                self._nodes.pop(nid)
                self._successors.pop(nid, None)
                self._predecessors.pop(nid, None)
            self._insertion_order = deque(
                x for x in self._insertion_order if x not in stale
            )
            self._edges = [
                e
                for e in self._edges
                if e.from_id not in stale and e.to_id not in stale
            ]
            self._prune_count += len(stale)
            return len(stale)

    # -- stats --------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "nodes_added_total": self._nodes_added,
            "edges_added_total": self._edges_added,
            "cycle_rejections": self._cycle_rejections,
            "pruned_total": self._prune_count,
        }

    # -- internals ----------------------------------------------------------

    def _has_cycle(self, start: str) -> bool:
        """O(V+E) DFS cycle check.  Called under lock (synchronous)."""
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)
            for nxt in self._successors.get(node, []):
                if nxt not in visited:
                    if dfs(nxt):
                        return True
                elif nxt in in_stack:
                    return True
            in_stack.discard(node)
            return False

        return dfs(start)


# ---------------------------------------------------------------------------
# Null-object sentinel
# ---------------------------------------------------------------------------

class NullTemporalGraph:
    """No-op implementation for when temporal reasoning is disabled."""

    async def add_node(self, node: TemporalNode) -> None:
        pass

    async def add_edge(self, edge: TemporalEdge) -> None:
        pass

    async def get_successors(self, node_id: str) -> Sequence[TemporalNode]:
        return []

    async def get_predecessors(self, node_id: str) -> Sequence[TemporalNode]:
        return []

    async def check_consistency(self) -> bool:
        return True

    async def prune(self, horizon_ns: int) -> int:
        return 0

    def stats(self) -> dict[str, int]:
        return {}
