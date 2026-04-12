"""
Knowledge Graph A* Pathfinder
=============================
Contributed by MemPalace-AGI (https://github.com/milla-jovovich/mempalace)

Semantic A* pathfinding over a :class:`TemporalKnowledgeGraph`. Finds the
lowest-cost path between two entities by traversing the triple graph.

Key features:

- **Bidirectional traversal**: triples ``(A, causes, B)`` are traversable
  as both A→B and B→A.
- **Predicate-based edge costs**: strong relationships (``causes``,
  ``subclass_of``) are cheaper to traverse than weak ones (``related_to``).
- **Pheromone modifier**: if a triple has high pheromone levels, its edge
  cost is reduced (the pathfinder "prefers" well-trodden paths).
- **Optional semantic heuristic**: if an embedding function is provided,
  the A* heuristic uses cosine similarity between entity embeddings. This
  dramatically prunes the search space. Without it, a graph-distance
  estimate is used instead.
- **Adaptive weighting**: when current and goal embeddings are very
  dissimilar (cross-domain), the heuristic blends graph and semantic
  estimates evenly. When they're in the same domain, semantic dominates.
- **Entity resolution**: case-insensitive matching with normalisation.

No external dependencies beyond the Python standard library and
:mod:`knowledge_graph.temporal_kg`.
"""

from __future__ import annotations

import heapq
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .temporal_kg import TemporalKnowledgeGraph

logger = logging.getLogger(__name__)


# ── Data models ────────────────────────────────────────────────────────


@dataclass
class PathResult:
    """Result of an A* pathfinding operation.

    Attributes
    ----------
    path : list of str
        Ordered entity names from start to goal.
    total_cost : float
        Accumulated traversal cost.
    nodes_explored : int
        Number of unique nodes popped from the open set.
    complete : bool
        True if the goal was reached.
    iterations : int
        Main-loop iterations executed.
    edges : list of dict
        Edge info for each consecutive pair in the path.
    """

    path: List[str] = field(default_factory=list)
    total_cost: float = 0.0
    nodes_explored: int = 0
    complete: bool = False
    iterations: int = 0
    edges: List[Dict[str, Any]] = field(default_factory=list)


# ── Constants ──────────────────────────────────────────────────────────

# Heuristic weights (from STAN_X v8 adaptive multi-objective heuristic)
CROSS_DOMAIN_THRESHOLD = 0.3
SAME_DOMAIN_SEMANTIC_WEIGHT = 0.9
SAME_DOMAIN_GRAPH_WEIGHT = 0.1
CROSS_DOMAIN_SEMANTIC_WEIGHT = 0.5
CROSS_DOMAIN_GRAPH_WEIGHT = 0.5
GRAPH_DISTANCE_SCALE = 0.5

# Base edge costs by predicate (lower = stronger relationship)
BASE_COSTS: Dict[str, float] = {
    "causes": 0.3,
    "caused_by": 0.3,
    "bidirectionally_causes": 0.25,
    "associated_with": 0.5,
    "correlated_with": 0.6,
    "possibly_causes": 0.7,
    "related_to": 0.8,
    "produced_by": 0.4,
    "belongs_to_domain": 0.5,
    "involves_variable": 0.4,
    "in_phase": 0.6,
    "structurally_similar": 0.5,
    "instance_of": 0.3,
    "subclass_of": 0.25,
    "scales_with": 0.35,
}
DEFAULT_BASE_COST = 0.5


# ── Helpers ────────────────────────────────────────────────────────────


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Cosine similarity between two vectors (pure Python, no numpy)."""
    if len(v1) != len(v2) or len(v1) == 0:
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    sim = dot / (norm1 * norm2)
    return max(0.0, min(1.0, sim))


def _normalise(entity: str) -> str:
    """Normalise entity name for lookup."""
    return entity.lower().replace(" ", "_").replace("'", "")


# ── Pathfinder ─────────────────────────────────────────────────────────


class KGPathfinder:
    """A* pathfinder over a :class:`TemporalKnowledgeGraph`.

    Parameters
    ----------
    kg : TemporalKnowledgeGraph
        The knowledge graph to search over.
    """

    def __init__(self, kg: TemporalKnowledgeGraph) -> None:
        self.kg = kg
        # Cache embeddings to avoid redundant calls
        self._embedding_cache: Dict[str, Optional[List[float]]] = {}
        # Temporal filter — set per find_path() call
        self._valid_at: Optional[str] = None
        self._embedding_fn: Optional[Callable] = None

    # ── Public API ─────────────────────────────────────────────────────

    def find_path(
        self,
        start: str,
        goal: str,
        max_hops: int = 5,
        embedding_fn: Optional[Callable[[str], Optional[List[float]]]] = None,
        valid_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find the lowest-cost path between two entities using A*.

        Parameters
        ----------
        start : str
            Starting entity name.
        goal : str
            Goal entity name.
        max_hops : int
            Maximum path length (default 5). Also caps A* iterations at
            ``max_hops * 500`` to prevent runaway searches.
        embedding_fn : callable or None
            Optional function ``entity_name → embedding_vector``.
            If provided, enables the semantic A* heuristic for faster
            convergence. The vector can be a list of floats or any
            sequence. If ``None``, falls back to a graph-distance
            heuristic.
        valid_at : str or None
            Optional ISO-8601 timestamp for temporal edge filtering.
            When provided, only triples whose temporal range includes
            this point in time are traversed (``valid_at <= t`` and
            ``invalid_at IS NULL OR invalid_at > t``).  When ``None``
            (default), only the standard ``invalid_at IS NULL`` filter
            is applied, preserving backward-compatible behaviour.

        Returns
        -------
        dict
            Keys: ``path`` (list of entity names), ``cost`` (float),
            ``hops`` (int), ``complete`` (bool), ``nodes_explored`` (int),
            ``edges`` (list of edge info dicts).
        """
        self._embedding_cache.clear()
        self._embedding_fn = embedding_fn
        self._valid_at = valid_at

        start_id = _normalise(start)
        goal_id = _normalise(goal)

        logger.info("A* search: %s → %s (max_hops=%d)", start_id, goal_id, max_hops)

        # Trivial case
        if start_id == goal_id:
            return {
                "path": [start_id],
                "cost": 0.0,
                "hops": 0,
                "complete": True,
                "nodes_explored": 1,
                "edges": [],
            }

        # Verify both entities exist
        if not self._entity_exists(start_id):
            logger.warning("Start entity %r not found in KG", start_id)
            return self._empty_result()

        if not self._entity_exists(goal_id):
            logger.warning("Goal entity %r not found in KG", goal_id)
            return self._empty_result()

        # A* search
        max_iterations = max_hops * 500
        open_set: List[tuple] = []  # (f_score, counter, node_id)
        closed_set: Set[str] = set()
        came_from: Dict[str, str] = {}
        g_score: Dict[str, float] = {start_id: 0.0}

        h_start = self._heuristic(start_id, goal_id)
        f_score: Dict[str, float] = {start_id: h_start}

        counter = 0
        heapq.heappush(open_set, (f_score[start_id], counter, start_id))
        counter += 1

        nodes_explored = 0
        iterations = 0

        while open_set and iterations < max_iterations:
            iterations += 1
            _, _, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            nodes_explored += 1

            # Goal reached!
            if current == goal_id:
                path = self._reconstruct_path(came_from, current)
                edges = self._collect_edges(path)
                return {
                    "path": path,
                    "cost": round(g_score[current], 4),
                    "hops": len(path) - 1,
                    "complete": True,
                    "nodes_explored": nodes_explored,
                    "edges": edges,
                }

            closed_set.add(current)

            # Check hop limit
            depth = self._path_depth(came_from, current)
            if depth >= max_hops:
                continue

            # Expand neighbours
            for neighbour in self._get_neighbours(current):
                if neighbour in closed_set:
                    continue

                edge_cost = self._edge_cost(current, neighbour)
                tentative_g = g_score[current] + edge_cost

                if neighbour not in g_score or tentative_g < g_score[neighbour]:
                    came_from[neighbour] = current
                    g_score[neighbour] = tentative_g
                    h = self._heuristic(neighbour, goal_id)
                    f = tentative_g + h
                    f_score[neighbour] = f
                    heapq.heappush(open_set, (f, counter, neighbour))
                    counter += 1

        # No path found
        logger.warning(
            "No path %s→%s (explored %d nodes in %d iterations)",
            start_id,
            goal_id,
            nodes_explored,
            iterations,
        )
        return self._empty_result(nodes_explored=nodes_explored)

    # ── Graph interface (reads from TemporalKnowledgeGraph) ────────────

    def _get_neighbours(self, entity: str) -> List[str]:
        """Get all entities connected to *entity* via active triples.

        Bidirectional: checks both subject and object columns.
        Respects ``self._valid_at`` temporal filter when set.
        """
        if self._valid_at is not None:
            rows = self.kg._conn.execute(
                """SELECT subject, object FROM triples
                   WHERE (subject = ? OR object = ?)
                     AND (valid_at IS NULL OR valid_at <= ?)
                     AND (invalid_at IS NULL OR invalid_at > ?)""",
                (entity, entity, self._valid_at, self._valid_at),
            ).fetchall()
        else:
            rows = self.kg._conn.execute(
                """SELECT subject, object FROM triples
                   WHERE (subject = ? OR object = ?)
                     AND invalid_at IS NULL""",
                (entity, entity),
            ).fetchall()

        neighbours: Set[str] = set()
        for row in rows:
            s, o = row["subject"], row["object"]
            if s == entity:
                neighbours.add(o)
            else:
                neighbours.add(s)
        return list(neighbours)

    def _get_best_edge(
        self,
        source: str,
        target: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the best (highest-confidence) edge between source and target.

        Respects ``self._valid_at`` temporal filter when set.
        """
        if self._valid_at is not None:
            row = self.kg._conn.execute(
                """SELECT id, predicate, confidence FROM triples
                   WHERE ((subject = ? AND object = ?) OR (subject = ? AND object = ?))
                     AND (valid_at IS NULL OR valid_at <= ?)
                     AND (invalid_at IS NULL OR invalid_at > ?)
                   ORDER BY confidence DESC
                   LIMIT 1""",
                (source, target, target, source, self._valid_at, self._valid_at),
            ).fetchone()
        else:
            row = self.kg._conn.execute(
                """SELECT id, predicate, confidence FROM triples
                   WHERE ((subject = ? AND object = ?) OR (subject = ? AND object = ?))
                     AND invalid_at IS NULL
                   ORDER BY confidence DESC
                   LIMIT 1""",
                (source, target, target, source),
            ).fetchone()

        if row is None:
            return None

        return {
            "triple_id": row["id"],
            "predicate": row["predicate"],
            "confidence": float(row["confidence"]) if row["confidence"] else 0.5,
        }

    def _edge_cost(self, source: str, target: str) -> float:
        """Compute traversal cost from source to target."""
        edge = self._get_best_edge(source, target)
        if edge is None:
            return 1.0

        pred = edge["predicate"]
        base_cost = BASE_COSTS.get(pred, DEFAULT_BASE_COST)

        # High confidence → lower cost
        conf = edge["confidence"]
        cost = base_cost * (1.0 - conf * 0.3)

        # Apply pheromone modifier
        modifier = self.kg.get_pheromone_modifier(edge["triple_id"])
        cost *= modifier

        return cost

    def _entity_exists(self, entity: str) -> bool:
        """Check if an entity exists in the KG (as subject or object).

        Respects ``self._valid_at`` temporal filter when set — an entity
        only "exists" if at least one of its triples is temporally valid.
        """
        if self._valid_at is not None:
            row = self.kg._conn.execute(
                """SELECT 1 FROM triples
                   WHERE (subject = ? OR object = ?)
                     AND (valid_at IS NULL OR valid_at <= ?)
                     AND (invalid_at IS NULL OR invalid_at > ?)
                   LIMIT 1""",
                (entity, entity, self._valid_at, self._valid_at),
            ).fetchone()
        else:
            row = self.kg._conn.execute(
                """SELECT 1 FROM triples
                   WHERE (subject = ? OR object = ?)
                   LIMIT 1""",
                (entity, entity),
            ).fetchone()
        return row is not None

    # ── Heuristic ──────────────────────────────────────────────────────

    def _heuristic(self, current: str, goal: str) -> float:
        """Adaptive heuristic h(n).

        With embedding function:
          Same-domain:  h = 0.9·h_semantic + 0.1·h_graph
          Cross-domain: h = 0.5·h_semantic + 0.5·h_graph

        Without embedding function:
          h = graph-distance estimate (based on neighbour count).
        """
        if current == goal:
            return 0.0

        # Try semantic heuristic if embeddings are available
        if self._embedding_fn is not None:
            current_emb = self._get_embedding(current)
            goal_emb = self._get_embedding(goal)

            if current_emb is not None and goal_emb is not None:
                similarity = _cosine_similarity(current_emb, goal_emb)
                h_semantic = 1.0 - similarity

                # Graph distance estimate
                neighbours = self._get_neighbours(current)
                connectivity = max(0.1, min(1.0, len(neighbours) / 20.0))
                h_graph = min(
                    1.0,
                    (h_semantic / connectivity) * GRAPH_DISTANCE_SCALE,
                )

                # Adaptive weighting
                if similarity < CROSS_DOMAIN_THRESHOLD:
                    w_sem = CROSS_DOMAIN_SEMANTIC_WEIGHT
                    w_graph = CROSS_DOMAIN_GRAPH_WEIGHT
                else:
                    w_sem = SAME_DOMAIN_SEMANTIC_WEIGHT
                    w_graph = SAME_DOMAIN_GRAPH_WEIGHT

                h = w_sem * h_semantic + w_graph * h_graph
                return max(0.0, min(1.0, h))

        # Fallback: graph-distance heuristic
        neighbours = self._get_neighbours(current)
        if goal in neighbours:
            return 0.1  # directly connected
        connectivity = max(0.1, min(1.0, len(neighbours) / 20.0))
        return min(1.0, GRAPH_DISTANCE_SCALE / connectivity)

    def _get_embedding(self, entity: str) -> Optional[List[float]]:
        """Get (cached) embedding for an entity."""
        if entity in self._embedding_cache:
            return self._embedding_cache[entity]

        emb = None
        if self._embedding_fn is not None:
            try:
                emb = self._embedding_fn(entity)
            except Exception as exc:
                logger.debug(
                    "Embedding lookup failed for %s: %s",
                    entity,
                    exc,
                )

        self._embedding_cache[entity] = emb
        return emb

    # ── Path reconstruction ────────────────────────────────────────────

    def _reconstruct_path(
        self,
        came_from: Dict[str, str],
        current: str,
    ) -> List[str]:
        """Walk back through came_from to build the path."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def _collect_edges(self, path: List[str]) -> List[Dict[str, Any]]:
        """Collect edge info for each consecutive pair in the path."""
        edges = []
        for i in range(len(path) - 1):
            edge = self._get_best_edge(path[i], path[i + 1])
            if edge:
                edges.append(
                    {
                        "source": path[i],
                        "target": path[i + 1],
                        **edge,
                    }
                )
            else:
                edges.append(
                    {
                        "source": path[i],
                        "target": path[i + 1],
                        "triple_id": "",
                        "predicate": "unknown",
                        "confidence": 0.0,
                    }
                )
        return edges

    def _path_depth(self, came_from: Dict[str, str], node: str) -> int:
        """Count how many hops from the start to reach this node."""
        depth = 0
        while node in came_from:
            node = came_from[node]
            depth += 1
        return depth

    @staticmethod
    def _empty_result(nodes_explored: int = 0) -> Dict[str, Any]:
        """Return an empty / failed path result."""
        return {
            "path": [],
            "cost": 0.0,
            "hops": 0,
            "complete": False,
            "nodes_explored": nodes_explored,
            "edges": [],
        }
