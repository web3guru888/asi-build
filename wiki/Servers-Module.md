# Servers Module — Kenny Graph MCP + SSE Bridge

The `servers` module provides **real-time external access** to Kenny Graph, a Memgraph (Neo4j-compatible) knowledge database with 89,574 nodes and 96,871 relationships. It exposes the graph via two complementary protocols: **MCP** (Model Context Protocol) for tool-augmented LLM clients, and **SSE** (Server-Sent Events) for web and streaming clients.

## Key Numbers

| Metric | Value |
|--------|-------|
| Source files | 2 |
| Total LOC | 1,020 |
| Kenny Graph nodes | 89,574 |
| Kenny Graph relationships | 96,871 |
| Agent army size | 1,405 autonomous agents |
| Agent teams | 48 |
| SSE update interval | 5 seconds |
| Public endpoint | `http://13.213.179.32:8090/sse` |

## Module Structure

```
src/asi_build/servers/
├── __init__.py
├── kenny_graph_sse_server.py   # FastAPI SSE server (522 LOC)
├── kenny_mcp_server.py         # MCP protocol server (498 LOC)
├── API_DOCUMENTATION.md        # Full API reference
└── README.md                   # Quick-start guide
```

## What is Kenny Graph?

Kenny Graph is an external Memgraph database that serves as the persistent knowledge substrate for ASI:BUILD's broader agent ecosystem. It stores conceptual relationships, agent state, and accumulated knowledge built up over time by 1,405 autonomous agents organized into 48 teams.

The `servers` module bridges this external knowledge network into ASI:BUILD by providing structured query and streaming access.

## Server 1: `kenny_mcp_server.py` — MCP Protocol

### Overview

Implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) — the emerging standard for tool-augmented LLMs. Any MCP-compatible client (Claude, Cursor, VS Code plugins, custom agents) can connect and execute live Cypher queries against the 89K-node graph.

### MCP Resources

```
kenny://graph/stats         — Overall graph statistics (node/edge counts)
kenny://graph/nodes         — Node browser (by type)
kenny://graph/relationships — Relationship browser
kenny://agent/status        — Live status of 1,405 agents across 48 teams
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `query_kenny_graph` | Execute arbitrary Cypher queries |
| `search_kenny_concepts` | Full-text search over concept names/descriptions |
| `get_node_relationships` | Expand a node's complete relationship neighborhood |
| `analyze_connectivity` | Run centrality, cluster detection, or shortest-path analysis |

### Example: Query Cypher via MCP

```python
# Any MCP client can call:
{
  "tool": "query_kenny_graph",
  "arguments": {
    "query": "MATCH (c:Concept)-[:RELATES_TO]->(k:Knowledge) RETURN c.name, k.content LIMIT 10",
    "limit": 10
  }
}
```

### Example: Search Concepts

```python
{
  "tool": "search_kenny_concepts",
  "arguments": {
    "search_term": "consciousness",
    "limit": 5
  }
}
```

## Server 2: `kenny_graph_sse_server.py` — SSE Streaming

### Overview

A FastAPI application that streams real-time snapshots of Kenny Graph state every 5 seconds. Any HTTP client — web browser, curl, Python requests — can subscribe and receive live updates.

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /sse/kenny-graph` | Graph node/edge counts + type distribution |
| `GET /sse/supervisor` | Agent army health metrics |
| `GET /sse/combined` | Full stats bundle (graph + analysis + supervisor) |
| `GET /stats/current` | One-shot JSON snapshot (no streaming) |
| `GET /health` | Health check (graph connectivity, DB availability) |
| `GET /demo` | Built-in HTML demo page for browser testing |

### SSE Event Format

Each event is a JSON blob pushed with `data:` prefix:

```json
{
  "timestamp": "2026-04-12T04:45:00.123Z",
  "status": "healthy",
  "nodes": 89574,
  "relationships": 96871,
  "node_types": ["Concept", "Agent", "Knowledge", "Task"],
  "relationship_types": ["RELATES_TO", "KNOWS", "ASSIGNED_TO"],
  "recent_activity": [...]
}
```

### Quick Start: curl

```bash
# Live streaming (press Ctrl+C to stop)
curl -N http://13.213.179.32:8090/sse/kenny-graph

# Live combined stream
curl -N http://13.213.179.32:8090/sse/combined

# One-shot snapshot
curl http://13.213.179.32:8090/stats/current | python3 -m json.tool

# Health check
curl http://13.213.179.32:8090/health
```

### Quick Start: Python EventSource

```python
import httpx

async def stream_kenny_graph():
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", "http://13.213.179.32:8090/sse/kenny-graph") as r:
            async for line in r.aiter_lines():
                if line.startswith("data:"):
                    data = json.loads(line[5:])
                    print(f"Nodes: {data['nodes']}, Rels: {data['relationships']}")
```

### Quick Start: Browser

Navigate to `http://13.213.179.32:8090/demo` to see a live updating dashboard of Kenny Graph statistics.

## Architecture Position

```
┌───────────────────────────────────────────────────┐
│              ASI:BUILD Runtime                    │
│                                                   │
│  ┌────────────────┐   ┌────────────────────────┐  │
│  │ Cognitive      │   │     servers module     │  │
│  │ Blackboard     │   │                        │  │
│  │ (internal)     │   │  kenny_mcp_server     │  │
│  │                │   │  kenny_sse_server     │  │
│  └────────────────┘   └──────────┬─────────────┘  │
│                                  │ bolt://         │
└──────────────────────────────────│─────────────────┘
                                   ▼
                          ┌─────────────────┐
                          │  Kenny Graph    │
                          │  (Memgraph)     │
                          │  89,574 nodes   │
                          │  96,871 rels    │
                          └─────────────────┘
```

Currently the `servers` module is **standalone** — it reads from Kenny Graph and exposes it outward, but does not yet feed Kenny Graph events into the Cognitive Blackboard.

## Planned: KennyGraphBlackboardAdapter (Issue #89)

The next step is a `KennyGraphBlackboardAdapter` that:
1. Maintains a persistent SSE subscription to `/sse/combined`
2. Filters incoming events for cognitively significant changes (node additions, knowledge updates)
3. Publishes relevant facts as `BlackboardEntry` objects with topic `knowledge_graph.external`
4. Runs as an async background task — no blocking on the cognitive cycle

This would make Kenny Graph's 89,574 nodes continuously available to all 29 ASI:BUILD modules via standard Blackboard queries.

### Design Sketch

```python
class KennyGraphBlackboardAdapter:
    """Streams Kenny Graph events → Cognitive Blackboard."""

    RELEVANT_NODE_TYPES = {"Concept", "Knowledge", "Insight"}

    def __init__(self, blackboard: CognitiveBlackboard, sse_url: str):
        self.blackboard = blackboard
        self.sse_url = sse_url

    async def run(self):
        """Persistent SSE subscription loop."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", f"{self.sse_url}/sse/kenny-graph") as r:
                async for line in r.aiter_lines():
                    if line.startswith("data:"):
                        event = json.loads(line[5:])
                        await self._handle_event(event)

    async def _handle_event(self, event: dict):
        """Filter and publish to Blackboard."""
        for node_type in self.RELEVANT_NODE_TYPES:
            if node_type in event.get("node_types", []):
                entry = BlackboardEntry(
                    module_id="servers.kenny_graph",
                    topic="knowledge_graph.external",
                    data={"source": "kenny_graph", "snapshot": event},
                    confidence=0.85,
                )
                await self.blackboard.post(entry)
```

## Future: Bidirectional Sync

Long term: ASI:BUILD's internal `knowledge_graph` module (bi-temporal, 24+ Cypher functions) could **push** high-confidence inferences back to Kenny Graph — creating a bidirectional knowledge exchange loop where ASI:BUILD's temporal reasoning enriches the persistent knowledge base.

## Related Issues

| Issue | Title |
|-------|-------|
| [#89](https://github.com/web3guru888/asi-build/issues/89) | Wire Kenny Graph SSE stream to Cognitive Blackboard |

## Related Discussions

| Discussion | Topic |
|------------|-------|
| [#98](https://github.com/web3guru888/asi-build/discussions/98) | Show & Tell: Inside the Servers Module |
| [#20](https://github.com/web3guru888/asi-build/discussions/20) | Show & Tell: Rings Network SDK |

## See Also

- [Cognitive Blackboard](Cognitive-Blackboard) — internal module-to-module communication
- [Knowledge Graph](Knowledge-Graph) — ASI:BUILD's bi-temporal internal knowledge store
- [Integrations Module](Integrations-Module) — LangChain, MCP, LangGraph tooling
- [Kenny-Graph-MCP-Server](Kenny-Graph-MCP-Server) — companion wiki page
