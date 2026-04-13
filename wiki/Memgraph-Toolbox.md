# Memgraph Toolbox

The `memgraph_toolbox` module provides a lightweight, extensible Python toolbox for interacting with [Memgraph](https://memgraph.com/) — a high-performance in-memory graph database with native Cypher support. It implements a **tool registry pattern** where each database capability (PageRank, betweenness centrality, schema inspection, Cypher queries) is encapsulated as a discoverable, schema-validated tool.

## At a Glance

| Attribute | Value |
|-----------|-------|
| **Path** | `src/asi_build/memgraph_toolbox/` |
| **LOC** | 917 |
| **Files** | 21 |
| **Architecture** | `BaseToolbox` registry + `BaseTool` interface |
| **Transport** | Neo4j Bolt protocol (via `neo4j` Python driver) |
| **Algorithms** | PageRank, Betweenness Centrality, Cypher |
| **Inspection** | Schema, Config, Index, Constraint, Storage, Triggers |
| **Tests** | `test_toolbox.py`, `test_tools.py` |

---

## Architecture

The module uses a two-layer design:

```
MemgraphToolbox          # concrete toolbox with all 9 tools
    └── BaseToolbox      # tool registry (name → BaseTool)
          └── BaseTool   # abstract interface (name, description, input_schema, call())
```

Tools communicate with Memgraph through the `Memgraph` client class, which wraps the Neo4j Bolt driver with:
- **Env-var fallback**: reads `MEMGRAPH_URL`, `MEMGRAPH_USER`, `MEMGRAPH_PASSWORD`, `MEMGRAPH_DATABASE`
- **Connectivity verification**: raises `ValueError` on connection or auth failure at init time
- **Implicit transaction fallback**: handles Memgraph-specific implicit-transaction errors that the Neo4j driver doesn't surface cleanly

---

## Quick Start

```python
from asi_build.memgraph_toolbox import MemgraphToolbox
from asi_build.memgraph_toolbox.api.memgraph import Memgraph

# Connect to Memgraph (or set MEMGRAPH_URL env var)
db = Memgraph(url="bolt://localhost:7687", username="", password="")

# Initialize the toolbox — all 9 tools registered automatically
toolbox = MemgraphToolbox(db=db)

# List available tools
tools = toolbox.get_all_tools()
for tool in tools:
    print(f"{tool.name}: {tool.description}")
```

**Output:**
```
run_betweenness_centrality: Calculates betweenness centrality for nodes in a graph...
show_config: Shows the configuration settings for Memgraph
show_constraint_info: Shows the constraint information for a Memgraph database
run_cypher: Executes a Cypher query on a Memgraph database
show_index_info: Shows the index information for a Memgraph database
page_rank: Calculates PageRank on a graph in Memgraph
show_schema_info: Shows the schema information for a Memgraph database
show_storage_info: Shows the storage information for a Memgraph database
show_triggers: Shows the triggers for a Memgraph database
```

---

## The `Memgraph` Client

```python
from asi_build.memgraph_toolbox.api.memgraph import Memgraph

db = Memgraph(
    url="bolt://localhost:7687",    # or MEMGRAPH_URL env var
    username="",                    # or MEMGRAPH_USER env var
    password="",                    # or MEMGRAPH_PASSWORD env var
    database="memgraph",            # or MEMGRAPH_DATABASE env var
    driver_config=None,             # passed to neo4j.GraphDatabase.driver()
)

# Execute any Cypher query
results = db.query("MATCH (n) RETURN n.name AS name LIMIT 10")
# Returns: List[Dict[str, Any]]

db.close()
```

The `query()` method handles both standard and implicit-transaction Memgraph paths, including:
- `CALL ... IN TRANSACTIONS` errors (common in Memgraph MAGE procedures)
- `SchemaInfo disabled` errors (Memgraph configuration-dependent)

---

## Tool Reference

### Cypher Tool — `run_cypher`

Execute arbitrary Cypher queries:

```python
tool = toolbox.get_tool("run_cypher")
results = tool.call({"query": "MATCH (n:Person) RETURN n.name LIMIT 5"})
```

**Input schema:**
```json
{
  "query": "string (required) — Cypher query to execute"
}
```

### PageRank Tool — `page_rank`

Runs the MAGE `pagerank.get()` procedure. Requires Memgraph MAGE to be installed:

```python
tool = toolbox.get_tool("page_rank")
results = tool.call({"limit": 20})
# Returns: [{"node": {...}, "rank": 0.0023}, ...]
```

**Input schema:**
```json
{
  "limit": "integer (default: 10) — max nodes to return"
}
```

> ⚠️ **Note**: `pagerank.get()` requires Memgraph MAGE. See the `TODO` in the source: this will fail if MAGE is not installed.

### Betweenness Centrality Tool — `run_betweenness_centrality`

Runs `betweenness_centrality.get()` (also MAGE):

```python
tool = toolbox.get_tool("run_betweenness_centrality")
results = tool.call({
    "isDirectionIgnored": True,   # treat graph as undirected
    "limit": 10
})
# Returns: [{"node": {...}, "betweenness_centrality": 0.412}, ...]
```

**Input schema:**
```json
{
  "isDirectionIgnored": "boolean (default: true) — ignore edge direction",
  "limit": "integer (default: 10) — max nodes to return"
}
```

### Inspection Tools

| Tool name | Cypher equivalent | Use case |
|-----------|------------------|----------|
| `show_schema_info` | `SHOW SCHEMA INFO` | Node labels, relationship types, property keys |
| `show_config` | `SHOW CONFIG` | Memgraph runtime configuration |
| `show_index_info` | `SHOW INDEX INFO` | Active indexes and their types |
| `show_constraint_info` | `SHOW CONSTRAINT INFO` | Uniqueness and existence constraints |
| `show_storage_info` | `SHOW STORAGE INFO` | Disk/memory usage |
| `show_triggers` | `SHOW TRIGGERS` | Active database triggers |

All inspection tools take an empty arguments dict:

```python
schema = toolbox.get_tool("show_schema_info").call({})
config = toolbox.get_tool("show_config").call({})
```

---

## Extending with Custom Tools

```python
from asi_build.memgraph_toolbox.api.tool import BaseTool
from asi_build.memgraph_toolbox.api.toolbox import BaseToolbox

class ShortestPathTool(BaseTool):
    def __init__(self, db):
        super().__init__(
            name="shortest_path",
            description="Find the shortest path between two nodes",
            input_schema={
                "type": "object",
                "properties": {
                    "start_id": {"type": "integer", "description": "Source node ID"},
                    "end_id": {"type": "integer", "description": "Target node ID"},
                },
                "required": ["start_id", "end_id"],
            },
        )
        self.db = db

    def call(self, arguments):
        query = """
        MATCH p = shortestPath((a)-[*]-(b))
        WHERE id(a) = $start_id AND id(b) = $end_id
        RETURN [node IN nodes(p) | node.name] AS path
        """
        return self.db.query(query, arguments)

# Add to existing toolbox
toolbox.add_tool(ShortestPathTool(db))
path = toolbox.get_tool("shortest_path").call({"start_id": 1, "end_id": 42})
```

---

## Integration with Other Modules

The toolbox is the foundation for several higher-level ASI:BUILD components:

| Module | How it uses memgraph_toolbox |
|--------|------------------------------|
| `integrations` | LangChain tools wrap `run_cypher` and `page_rank` for NL→Cypher pipelines |
| `servers` (Kenny Graph) | MCP server exposes all 9 tools over Model Context Protocol |
| `knowledge_graph` | Uses `run_cypher` for bi-temporal triple writes |
| `graph_intelligence` | Uses `run_betweenness_centrality` and `page_rank` to seed FastToG community scoring |

### Using with LangChain

```python
from langchain.tools import Tool
from asi_build.memgraph_toolbox import MemgraphToolbox

# Wrap each toolbox tool as a LangChain tool
def make_lc_tool(toolbox_tool):
    return Tool(
        name=toolbox_tool.name,
        description=toolbox_tool.description,
        func=lambda args: toolbox_tool.call(args),
    )

lc_tools = [make_lc_tool(t) for t in toolbox.get_all_tools()]
```

### Using with MCP (Model Context Protocol)

The `servers` module exposes the toolbox via FastMCP:

```python
# From servers/kenny_graph_mcp.py
from mcp.server.fastmcp import FastMCP
from asi_build.memgraph_toolbox import MemgraphToolbox

mcp = FastMCP("kenny-graph-mcp")

@mcp.tool()
def run_query(cypher: str) -> list:
    return toolbox.get_tool("run_cypher").call({"query": cypher})

@mcp.tool()
def get_page_rank(limit: int = 10) -> list:
    return toolbox.get_tool("page_rank").call({"limit": limit})
```

---

## Connection Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `MEMGRAPH_URL` | `bolt://localhost:7687` | Bolt connection URL |
| `MEMGRAPH_USER` | `""` | Username (Memgraph is unauthenticated by default) |
| `MEMGRAPH_PASSWORD` | `""` | Password |
| `MEMGRAPH_DATABASE` | `"memgraph"` | Database name |

---

## Known Limitations

1. **MAGE dependency**: `page_rank` and `run_betweenness_centrality` require [Memgraph MAGE](https://github.com/memgraph/mage) extensions to be installed. Without MAGE, these will raise a `QueryError`.

2. **No async support**: All tools are synchronous. For async use, wrap in `asyncio.to_thread()` or use `ThreadPoolExecutor`.

3. **No connection pooling**: The `Memgraph` client creates a single driver instance. For high-throughput use, consider connection pool management.

4. **Schema inspection Memgraph-version dependent**: `SHOW SCHEMA INFO` behavior varies across Memgraph versions.

---

## Related Pages

- [Integrations Module](Integrations-Module) — LangChain + MCP layers built on this toolbox
- [Kenny Graph MCP Server](Kenny-Graph-MCP-Server) — live Kenny Graph exposed via MCP
- [Graph Intelligence](Graph-Intelligence) — FastToG reasoning using Memgraph as knowledge store
- [Knowledge Graph](Knowledge-Graph) — bi-temporal KG that can use Memgraph as backend
- [Module Index](Module-Index) — all 29 modules at a glance
