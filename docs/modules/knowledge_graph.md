# Knowledge Graph

> **Maturity**: `stable` · **Adapter**: `KnowledgeGraphAdapter`

The only `stable`-maturity module in ASI:BUILD. Implements a temporal knowledge graph backed by SQLite with bi-temporal triples (valid time + transaction time), provenance tracking, and automatic contradiction detection. Each triple stores subject, predicate, object along with timestamps and confidence scores. The KGPathfinder provides semantic A* pathfinding between entities, enabling discovery of indirect relationships across the graph.

This is the foundational knowledge storage layer used by many other modules.

## Key Classes

| Class | Description |
|-------|-------------|
| `TemporalKnowledgeGraph` | Bi-temporal triple store with provenance, contradiction detection, CRUD operations |
| `KGPathfinder` | Semantic A* pathfinding between entities |

## Example Usage

```python
from asi_build.knowledge_graph import TemporalKnowledgeGraph, KGPathfinder
kg = TemporalKnowledgeGraph(db_path="knowledge.db")
kg.add_triple("solar_flares", "correlates_with", "magnetic_storms", confidence=0.87)
kg.add_triple("magnetic_storms", "affects", "satellite_orbits", confidence=0.93)
path = KGPathfinder(kg).find_path("solar_flares", "satellite_orbits")
```

## Blackboard Integration

KnowledgeGraphAdapter publishes new triples, contradiction alerts, pathfinding results, and graph statistics; consumes reasoning inferences for automatic triple ingestion.
