# Integrations Module

The `integrations` module connects ASI:BUILD's cognitive architecture to the broader AI tooling ecosystem. It provides three production-quality bridges: a **LangChain-Memgraph integration**, an **MCP server for Memgraph**, and an **SQL-to-Memgraph migration agent** — all built on top of the `memgraph_toolbox` library.

---

## Overview

| Sub-module | Purpose | LOC | Status |
|------------|---------|-----|--------|
| `langchain-memgraph` | LangChain tools and chains for Memgraph graph databases | ~543 | ✅ Functional |
| `mcp-memgraph` | Model Context Protocol server exposing Memgraph to LLM agents | ~378 | ✅ Functional |
| `agents` | LangGraph-powered SQL→Memgraph migration agent | ~4,912 | ✅ Functional |

**Total**: 49 Python files · 7,217 LOC

---

## 1. LangChain-Memgraph Integration (`langchain-memgraph`)

Provides first-class LangChain primitives for interacting with Memgraph graph databases.

### Package: `langchain_memgraph`

```python
from langchain_memgraph import (
    MemgraphQAChain,        # Natural-language Q&A over graph data
    MemgraphLangChain,      # Core LangChain-Memgraph graph interface
    MemgraphLoader,         # Document loader from graph queries
    MemgraphRetriever,      # RAG retriever over graph traversals
    MemgraphToolkit,        # Full toolkit for agent use
)
```

### Toolkit Tools

The `MemgraphToolkit` bundles 9 tools that can be handed directly to any LangChain agent:

| Tool | Cypher Operation | Description |
|------|-----------------|-------------|
| `RunQueryTool` | `MATCH ... RETURN` | Execute arbitrary Cypher queries |
| `RunShowSchemaInfoTool` | `SHOW SCHEMA INFO` | Discover node labels and relationship types |
| `RunShowStorageInfoTool` | `SHOW STORAGE INFO` | Memory and disk usage stats |
| `RunShowConfigTool` | `SHOW CONFIG` | Memgraph configuration parameters |
| `RunShowTriggersTool` | `SHOW TRIGGERS` | List active Cypher triggers |
| `RunShowIndexInfoTool` | `SHOW INDEX INFO` | Index definitions and stats |
| `RunShowConstraintInfoTool` | `SHOW CONSTRAINT INFO` | Constraint definitions |
| `RunPageRankMemgraphTool` | PageRank algorithm | Node importance scoring |
| `RunBetweennessCentralityTool` | Betweenness centrality | Node centrality scoring |

### Quick Start

```python
from memgraph_toolbox.api.memgraph import Memgraph
from langchain_memgraph import MemgraphToolkit, MemgraphQAChain
from langchain_openai import ChatOpenAI

# Connect to Memgraph
db = Memgraph(url="bolt://localhost:7687")

# Build LangChain toolkit
toolkit = MemgraphToolkit(db=db, llm=ChatOpenAI())
tools = toolkit.get_tools()  # All 9 tools as LangChain Tool objects

# Natural-language Q&A
chain = MemgraphQAChain.from_llm(llm=ChatOpenAI(), graph=db)
result = chain.invoke("Which nodes have the highest PageRank?")
```

### MemgraphQAChain

The QA chain translates natural-language questions into Cypher, executes them, and returns natural-language answers:

```
User question → LLM generates Cypher → Memgraph executes → LLM formats result → Answer
```

---

## 2. MCP Server for Memgraph (`mcp-memgraph`)

Implements the [Model Context Protocol](https://modelcontextprotocol.io/) using **FastMCP**, exposing Memgraph as a tool server that any MCP-compatible LLM agent (Claude, GPT-4, etc.) can call.

### Architecture

```
LLM Agent (Claude/GPT) ──MCP protocol──► FastMCP server
                                              │
                                   ┌──────────▼──────────┐
                                   │   mcp-memgraph       │
                                   │   (stateless HTTP)   │
                                   └──────────┬──────────┘
                                              │ Bolt protocol
                                         ┌────▼────┐
                                         │ Memgraph │
                                         └─────────┘
```

### Exposed MCP Tools

```python
@mcp.tool()
def run_query(query: str) -> List[Dict[str, Any]]:
    """Run a Cypher query on Memgraph"""

@mcp.tool()
def get_schema() -> List[Dict[str, Any]]:
    """Get Memgraph schema information"""

@mcp.tool()
def get_storage() -> List[Dict[str, Any]]:
    """Get Memgraph storage information"""

@mcp.tool()
def get_configuration() -> List[Dict[str, Any]]:
    """Get Memgraph configuration"""

@mcp.tool()
def get_index() -> List[Dict[str, Any]]:
    """Get index information"""

@mcp.tool()
def get_constraint() -> List[Dict[str, Any]]:
    """Get constraint information"""

@mcp.tool()
def get_triggers() -> List[Dict[str, Any]]:
    """Get trigger information"""

@mcp.tool()
def get_betweenness_centrality() -> List[Dict[str, Any]]:
    """Compute betweenness centrality across the graph"""

@mcp.tool()
def get_page_rank() -> List[Dict[str, Any]]:
    """Compute PageRank for all nodes"""
```

### Running the Server

```bash
# Default: stdio transport (for Claude Desktop, etc.)
cd integrations/mcp-memgraph
uv run mcp-memgraph

# HTTP transport (for remote agents)
MCP_TRANSPORT=streamable-http uv run mcp-memgraph

# Configuration via environment
export MEMGRAPH_URL=bolt://localhost:7687
export MEMGRAPH_USER=your_user
export MEMGRAPH_PASSWORD=your_password
export MEMGRAPH_DATABASE=memgraph
```

### Connection to ASI:BUILD

The MCP server gives external LLM agents direct access to the knowledge graph stored in Memgraph — making ASI:BUILD's bi-temporal KG queryable by any AI agent that speaks MCP. Combined with the Kenny Graph SSE server (`servers` module), this creates a two-channel external interface:

| Channel | Protocol | Use case |
|---------|----------|----------|
| `mcp-memgraph` | MCP / HTTP | LLM agent tool calls |
| Kenny Graph SSE | Server-Sent Events | Real-time streaming subscribers |

---

## 3. SQL-to-Memgraph Migration Agent (`agents`)

A LangGraph-powered intelligent agent that migrates relational databases (MySQL, PostgreSQL) to Memgraph. Uses LLM reasoning to generate optimal graph models from SQL schemas.

**Files**: 22 Python files · 4,912 LOC  
**Dependencies**: LangGraph, LangChain, OpenAI GPT-4o-mini, memgraph_toolbox

### Architecture: LangGraph Workflow

```
        ┌─────────────────────────────────────────────────┐
        │              Migration Workflow                   │
        │                                                  │
        │  ┌──────────────┐    ┌──────────────────────┐   │
        │  │  Analyze SQL  │───►│  Generate Graph Model │   │
        │  │  Schema       │    │  (DETERMINISTIC or    │   │
        │  │  (DatabaseAnaly│   │   LLM_POWERED via     │   │
        │  │  zerFactory)  │    │   HyGM + GPT-4o-mini) │   │
        │  └──────────────┘    └──────────┬───────────┘   │
        │                                 │               │
        │                    ┌────────────▼────────────┐  │
        │                    │  [Optional] Interactive  │  │
        │                    │  Refinement Loop         │  │
        │                    │  (natural language edit) │  │
        │                    └────────────┬────────────┘  │
        │                                 │               │
        │                    ┌────────────▼────────────┐  │
        │                    │  Generate Cypher Queries │  │
        │                    │  (CypherGenerator)       │  │
        │                    └────────────┬────────────┘  │
        │                                 │               │
        │                    ┌────────────▼────────────┐  │
        │                    │  Execute Migration       │  │
        │                    │  + Validate Results      │  │
        │                    └─────────────────────────┘  │
        └─────────────────────────────────────────────────┘
```

### Graph Modeling Strategies

#### `DETERMINISTIC` (default)
Rule-based approach: maps SQL tables → nodes, foreign keys → relationships, applies standard naming conventions. Fast, predictable, no LLM call needed.

#### `LLM_POWERED`
Uses the **HyGM (Hypothetical Graph Modeling)** algorithm:

1. Schema analysis prompt → GPT-4o-mini generates `LLMGraphNode` and `LLMGraphRelationship` objects
2. LLM infers semantic relationships beyond foreign keys (e.g., `User` → `PURCHASED` → `Product`)
3. Structured output validated with Pydantic models
4. Optional: interactive refinement loop where the user can describe changes in natural language

```python
from asi_build.integrations.agents import SQLToMemgraphAgent
from asi_build.integrations.agents.core import GraphModelingStrategy

agent = SQLToMemgraphAgent(
    interactive_graph_modeling=True,         # Let user refine graph model
    graph_modeling_strategy=GraphModelingStrategy.LLM_POWERED,  # Use GPT
)

agent.run(
    source_db_config={
        "type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "myapp",
        "username": "postgres",
        "password": "...",
    },
    memgraph_config={
        "url": "bolt://localhost:7687",
    }
)
```

### Migration State Machine

The LangGraph workflow tracks migration state through a `MigrationState` TypedDict:

```python
class MigrationState(TypedDict):
    source_db_config: Dict[str, str]      # Source DB credentials
    memgraph_config: Dict[str, str]       # Memgraph connection
    database_structure: Dict[str, Any]    # Analyzed schema
    graph_model: Any                      # HyGM GraphModel
    migration_queries: List[str]          # Generated Cypher
    current_step: str                     # Workflow progress
    errors: List[str]                     # Error accumulation
    completed_tables: List[str]           # Migration progress
    total_tables: int                     # Total scope
    created_indexes: List[str]            # Applied indexes
    created_constraints: List[str]        # Applied constraints
```

### Database Support

The `DatabaseAnalyzerFactory` supports:
- **MySQL** — via `MySQLAnalyzer`
- **PostgreSQL** — via `PostgreSQLAnalyzer`
- Schema introspection: tables, columns, data types, foreign keys, indexes, constraints

---

## Integration with Cognitive Blackboard

The integrations module currently operates independently of ASI:BUILD's Cognitive Blackboard. There is an open opportunity to bridge it:

| Integration point | Blackboard topic | Value |
|------------------|-----------------|-------|
| MCP tool call results | `integrations.mcp.query_result` | Knowledge graph query results surfaced to reasoning |
| Migration completions | `integrations.migration.complete` | Trigger KG re-indexing on new graph data |
| Schema change events | `integrations.schema.change` | Invalidate cached KG pathfinder routes |
| PageRank results | `integrations.graph.pagerank` | Feed importance scores to GWT attention mechanism |

See Issue [#90](https://github.com/web3guru888/asi-build/issues/90) for implementation details.

---

## Installation

```bash
# LangChain integration
cd src/asi_build/integrations/langchain-memgraph
pip install -e .

# MCP server
cd src/asi_build/integrations/mcp-memgraph
uv run mcp-memgraph

# Migration agent (requires OpenAI API key)
cd src/asi_build/integrations/agents
export OPENAI_API_KEY=your_key
uv run main.py
```

---

## Related Pages

- [Knowledge-Graph](Knowledge-Graph) — bi-temporal KG that Memgraph stores
- [Kenny-Graph-MCP-Server](Kenny-Graph-MCP-Server) — ASI:BUILD's own SSE + MCP server for the KG
- [Cognitive-Blackboard](Cognitive-Blackboard) — integration hub for all modules
- [Roadmap](Roadmap) — Phase 2 integration priorities
