# Memgraph Toolbox

> **Maturity**: `experimental` · **Adapter**: `None`

Memgraph graph database toolbox providing Cypher query utilities and database management helpers. Currently a minimal placeholder module with no public API exports — functionality is primarily accessed through the graph_intelligence and integrations modules which provide higher-level abstractions over Memgraph.

Intended for direct Memgraph interaction when the higher-level APIs are insufficient.

## Key Classes

| Class | Description |
|-------|-------------|
| *(No public API classes exported)* | Utility scripts for direct Memgraph access |

## Example Usage

```python
# memgraph_toolbox is accessed indirectly through graph_intelligence
from asi_build.graph_intelligence import MemgraphConnection
conn = MemgraphConnection(host="localhost", port=7687)
# For direct Cypher queries, use the connection's execute method
results = conn.execute("MATCH (n) RETURN n LIMIT 10")
```

## Blackboard Integration

No blackboard adapter. Memgraph access is mediated through the graph_intelligence module's GraphIntelligenceAdapter.
