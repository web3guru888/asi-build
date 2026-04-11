"""
ASI:BUILD Knowledge Graph Module
================================
Contributed by MemPalace-AGI (https://github.com/milla-jovovich/mempalace)

Bi-temporal knowledge graph with provenance tracking, contradiction detection,
and semantic A* pathfinding. Designed for autonomous research systems that need
to track evolving knowledge with full temporal history.

Key features:
- Entity-relationship triples with bi-temporal validity (valid_at, invalid_at)
- Provenance tracking (agent, source, confidence scores)
- Automatic contradiction detection and resolution
- Temporal querying (point-in-time, range, history)
- Statement classification (observation, inference, hypothesis, fact)
- Semantic A* pathfinding between entities
"""

try:
    from .temporal_kg import TemporalKnowledgeGraph
except (ImportError, ModuleNotFoundError, SyntaxError):
    TemporalKnowledgeGraph = None
try:
    from .pathfinder import KGPathfinder
except (ImportError, ModuleNotFoundError, SyntaxError):
    KGPathfinder = None

__all__ = ["TemporalKnowledgeGraph", "KGPathfinder"]
