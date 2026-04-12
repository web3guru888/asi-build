# Integrations

> **Maturity**: `alpha` · **Adapter**: `IntegrationsBlackboardBridge`

External service bridges connecting ASI:BUILD to third-party platforms. Provides LangChain-Memgraph integration for graph-based question answering and document retrieval, SQL-to-Graph migration agents using HyGM (Hybrid Graph Model), and an MCP (Model Context Protocol) server for Memgraph access.

All sub-packages require external dependencies (LangGraph, Neo4j driver, memgraph-toolbox).

## Key Classes

| Class | Description |
|-------|-------------|
| `agents` | SQL-to-Memgraph migration via HyGM |
| `langchain_memgraph` | LangChain graph QA, document loaders, retrievers |
| `mcp_memgraph` | MCP server for Memgraph Cypher queries |

## Example Usage

```python
from asi_build.integrations import langchain_memgraph
# Requires: pip install langchain neo4j
retriever = langchain_memgraph.GraphRetriever(uri="bolt://localhost:7687")
docs = retriever.get_relevant_documents("What causes solar flares?")
```

## Blackboard Integration

IntegrationsBlackboardBridge bridges external service results into the blackboard, publishing LangChain retrieval results and SQL-to-Graph migration status; consumes queries from reasoning and knowledge graph modules.
