"""Temporal-graph value types — Allen relations, nodes, edges, config."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, FrozenSet


class AllenRelation(Enum):
    """Allen's 13 interval relations (7 base + 6 inverse)."""

    # 7 base relations
    BEFORE = auto()           # A ends before B starts
    MEETS = auto()            # A ends exactly when B starts
    OVERLAPS = auto()         # A starts before B, ends inside B
    STARTS = auto()           # A and B start together; A ends first
    DURING = auto()           # A is fully inside B
    FINISHES = auto()         # A and B end together; B starts first
    EQUALS = auto()           # A and B are identical intervals

    # 6 inverses
    AFTER = auto()
    MET_BY = auto()
    OVERLAPPED_BY = auto()
    STARTED_BY = auto()
    CONTAINS = auto()
    FINISHED_BY = auto()


@dataclass(frozen=True)
class TemporalNode:
    """A single time-stamped cognitive event or world-state snapshot."""

    node_id: str                                     # UUID or stable hash
    timestamp_ns: int                                # time.time_ns() at creation
    state_snapshot: dict[str, Any]                   # shallow copy of relevant state
    tags: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class TemporalEdge:
    """Directed edge annotated with an Allen interval relation."""

    from_id: str
    to_id: str
    relation: AllenRelation
    duration_ns: int                                 # |to.timestamp_ns - from.timestamp_ns|


@dataclass(frozen=True)
class TemporalGraphConfig:
    """Tuning knobs for :class:`DictTemporalGraph`."""

    max_nodes: int = 10_000
    consistency_check: bool = True                   # enforce DAG on add_edge
    prune_horizon_s: float = 3600.0                  # prune nodes older than this
