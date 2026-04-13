# Kenny Graph MCP/SSE Server

The `servers/` module exposes ASI:BUILD's knowledge graph to external agents via two complementary protocols: **Server-Sent Events (SSE)** for real-time streaming queries, and **Model Context Protocol (MCP)** for LLM tool-calling integration.

**Location:** `src/asi_build/servers/`  
**Files:** 3 Python files  
**Total LOC:** ~1,024  

---

## Overview

Kenny Graph is a Memgraph-backed knowledge base with:
- **89,574 nodes**
- **96,871 relationships**
- Full Cypher query support
- Hosted on AWS Singapore (`ap-southeast-1`, `13.213.179.32`)

The server pair makes this graph accessible to any MCP-compatible AI agent or SSE-capable application in real time.

---

## Architecture

```
servers/
├── kenny_mcp_server.py      # MCP protocol server (498 LOC)
├── kenny_graph_sse_server.py # SSE streaming server (522 LOC)
└── __init__.py
```

---

## SSE Server (`kenny_graph_sse_server.py`)

Server-Sent Events provide a persistent, one-directional HTTP stream from server to client. Ideal for real-time knowledge updates.

### Endpoints

```
GET  http://13.213.179.32:8090/sse      # Subscribe to event stream
POST http://13.213.179.32:8090/message  # Send a query/tool call
```

### Example: Streaming a Cypher Query

```python
import httpx
import json

async def query_kenny(cypher: str):
    # Subscribe to SSE stream
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", "http://13.213.179.32:8090/sse") as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    yield event

# Execute a query via POST
async def run_query(cypher: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://13.213.179.32:8090/message",
            json={"tool": "run_query", "arguments": {"query": cypher}}
        )
        return response.json()

# Example: Find high-centrality concept nodes
result = await run_query("""
MATCH (n:Concept)
RETURN n.name, n.importance
ORDER BY n.importance DESC
LIMIT 10
""")
```

---

## MCP Server (`kenny_mcp_server.py`)

[Model Context Protocol](https://modelcontextprotocol.io/) is the emerging standard for connecting LLMs to external data sources and tools. The Kenny MCP server exposes 5 tools:

| Tool | Arguments | Description |
|------|-----------|-------------|
| `run_query` | `query: str` | Execute any Cypher query against Kenny Graph |
| `get_schema` | — | Get all node labels, relationship types, property keys |
| `get_configuration` | — | Fetch Memgraph server configuration |
| `get_index` | — | List all active indexes |
| `get_constraint_info` | — | Show active uniqueness/existence constraints |

### Connecting from Claude Desktop or Other MCP Clients

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kenny-graph": {
      "command": "python3",
      "args": ["/path/to/asi-build/src/asi_build/servers/kenny_mcp_server.py"],
      "env": {
        "MEMGRAPH_HOST": "13.213.179.32",
        "MEMGRAPH_PORT": "7687"
      }
    }
  }
}
```

Once connected, you can ask Claude: *"What are the top 10 most connected nodes in Kenny Graph?"* and it will call `run_query` with the appropriate Cypher.

---

## Memgraph Toolbox

The `memgraph_toolbox/` submodule provides a LangChain/LlamaIndex-compatible tool layer over any Memgraph instance (not just Kenny):

**Location:** `src/asi_build/memgraph_toolbox/`  
**Files:** 21 Python files  
**Framework:** LangChain `BaseTool` compatible

### Available Tools

```python
from memgraph_toolbox.memgraph_toolbox import MemgraphToolbox
from memgraph_toolbox.api.memgraph import Memgraph

db = Memgraph(url="bolt://localhost:7687", username="", password="")
toolbox = MemgraphToolbox(db)

# List all tools
for tool in toolbox.get_all_tools():
    print(f"{tool.name}: {tool.description}")
```

| Tool Class | Purpose |
|-----------|---------|
| `CypherTool` | Execute arbitrary Cypher queries |
| `ShowSchemaInfoTool` | Get node labels and relationship types |
| `PageRankTool` | Run PageRank algorithm (MAGE required) |
| `BetweennessCentralityTool` | Find high-centrality nodes |
| `ShowTriggersTool` | List active database triggers |
| `ShowStorageInfoTool` | Get storage metrics |
| `ShowIndexInfoTool` | List indexes |
| `ShowConstraintInfoTool` | Get constraint definitions |
| `ShowConfigTool` | Fetch server configuration |

### Using with LangChain

```python
from langchain.agents import initialize_agent
from langchain.chat_models import ChatOpenAI
from memgraph_toolbox.memgraph_toolbox import MemgraphToolbox

db = Memgraph(url="bolt://localhost:7687")
tools = MemgraphToolbox(db).get_all_tools()

agent = initialize_agent(
    tools=tools,
    llm=ChatOpenAI(model="gpt-4"),
    agent="zero-shot-react-description",
    verbose=True
)

agent.run("Find the 5 most connected nodes in the knowledge graph")
```

### Using with LlamaIndex

```python
from llama_index.tools import FunctionTool
from memgraph_toolbox.tools.cypher import CypherTool

cypher_tool = CypherTool(db)
llama_tool = FunctionTool.from_defaults(
    fn=lambda query: cypher_tool.call({"query": query}),
    name="run_graph_query",
    description="Execute a Cypher query on the knowledge graph"
)
```

---

## Integration with ASI:BUILD's Cognitive Architecture

The Kenny Graph server creates a **shared world-model** for multi-agent systems:

```
External Agent A ──► SSE subscribe ──► Kenny Graph ──► Blackboard entry
External Agent B ──► MCP tool call ──► Kenny Graph ──► Blackboard entry
ASI:BUILD modules ──► Rings Network ──► Kenny Graph ──► Blackboard entry
```

### Planned: Blackboard Integration (Issue #85)

When fully integrated with the Cognitive Blackboard:

```python
from asi_build.integration.blackboard import CognitiveBlackboard

class KennyGraphBlackboardAdapter:
    def __init__(self, blackboard: CognitiveBlackboard, kenny_sse_url: str):
        self.blackboard = blackboard
        self.kenny_url = kenny_sse_url
    
    async def subscribe_and_relay(self):
        """Stream Kenny Graph updates into the Blackboard."""
        async for event in self._stream_kenny_events():
            entry = BlackboardEntry(
                module_id="kenny_graph",
                data_type="knowledge_node",
                content=event,
                confidence=0.95
            )
            await self.blackboard.write(entry)
    
    async def query_via_blackboard(self, cypher: str) -> List[dict]:
        """Route Blackboard knowledge queries through Kenny Graph."""
        result = await self._run_query(cypher)
        return result
```

---

## Running Locally

### Start the SSE Server

```bash
cd src/asi_build/servers
python3 kenny_graph_sse_server.py --host 0.0.0.0 --port 8090
```

### Start the MCP Server

```bash
python3 kenny_mcp_server.py
```

### Connect Memgraph Toolbox to a Local Instance

```bash
# Start Memgraph (Docker)
docker run -d -p 7687:7687 -p 7444:7444 memgraph/memgraph

# Use the toolbox
python3 -c "
from memgraph_toolbox.api.memgraph import Memgraph
from memgraph_toolbox.memgraph_toolbox import MemgraphToolbox
db = Memgraph()
toolbox = MemgraphToolbox(db)
print([t.name for t in toolbox.get_all_tools()])
"
```

---

## Open Issues

- Issue [#85](https://github.com/web3guru888/asi-build/issues/85) — Wire Kenny Graph SSE stream to Cognitive Blackboard
- Future: WebSocket endpoint for bidirectional agent communication
- Future: Decentralized Kenny Graph replication via Rings Network

---

*See also:* [Cognitive-Blackboard](Cognitive-Blackboard), [Knowledge-Graph](Knowledge-Graph), [Rings-Network](Rings-Network)
