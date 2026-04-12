# Graph Intelligence

> **Maturity**: `beta` · **Adapter**: `GraphIntelligenceAdapter`

Graph-based reasoning and community detection using Memgraph as the backend. Provides a typed knowledge graph schema with 7 node types (UI elements, workflows, communities, applications, screens, patterns, errors), community detection algorithms (Louvain, Girvan-Newman), and schema management for graph structure evolution.

Supports FastToG-style graph reasoning for traversing knowledge structures.

## Key Classes

| Class | Description |
|-------|-------------|
| `KnowledgeGraphSchema` | Typed graph schema definition |
| `MemgraphConnection` | Memgraph database connection |
| `SchemaManager` | Schema migration and management |
| `NodeType` | Graph node type enum |
| `RelationshipType` | Graph relationship type enum |
| `UIElementNode` | Typed UI element graph node |
| `WorkflowNode` | Typed workflow graph node |
| `CommunityNode` | Typed community graph node |
| `ApplicationNode` | Typed application graph node |
| `ScreenNode` | Typed screen graph node |
| `PatternNode` | Typed pattern graph node |
| `ErrorNode` | Typed error graph node |
| `Relationship` | Typed graph edge |
| `create_ui_element` | Factory function for UI element nodes |
| `create_community` | Factory function for community nodes |
| `create_workflow` | Factory function for workflow nodes |

## Example Usage

```python
from asi_build.graph_intelligence import MemgraphConnection, SchemaManager, create_community
conn = MemgraphConnection(host="localhost", port=7687)
schema = SchemaManager(conn)
schema.initialize()
community = create_community(name="astrophysics", algorithm="louvain")
```

## Blackboard Integration

GraphIntelligenceAdapter publishes community detection results, graph statistics, and schema updates; consumes knowledge graph triples and reasoning outputs for graph-based analysis.
