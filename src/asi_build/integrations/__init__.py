"""
ASI:BUILD Integrations Module
=============================

Third-party integration packages for ASI:BUILD, including:

- **agents**: SQL-to-Memgraph migration agent with LLM-powered graph modeling (HyGM)
- **langchain-memgraph**: LangChain integration for Memgraph (graph QA, document loaders,
  retrievers, toolkits)
- **mcp-memgraph**: Model Context Protocol (MCP) server for Memgraph graph operations

These sub-packages have external dependencies (langchain, memgraph-toolbox, mysql-connector,
langgraph, etc.) that are not required by the core ASI:BUILD library.  Imports are guarded
so that missing optional dependencies raise clear errors only when the specific integration
is actually used, rather than at package-import time.
"""

__maturity__ = "alpha"

__all__ = [
    "agents",
    "langchain_memgraph",
    "mcp_memgraph",
]


def __getattr__(name: str):
    """Lazy imports so missing optional deps don't crash the top-level package."""

    if name == "agents":
        try:
            import importlib

            _agents = importlib.import_module("asi_build.integrations.agents")
            globals()["agents"] = _agents
            return _agents
        except ImportError as exc:
            raise ImportError(
                "The 'agents' integration requires additional dependencies "
                "(langgraph, langchain-openai, mysql-connector-python, memgraph-toolbox). "
                "Install them with: pip install langgraph langchain-openai "
                "mysql-connector-python memgraph-toolbox"
            ) from exc

    if name == "langchain_memgraph":
        try:
            import importlib

            _mod = importlib.import_module(
                "asi_build.integrations.langchain-memgraph.langchain_memgraph"
            )
            globals()["langchain_memgraph"] = _mod
            return _mod
        except (ImportError, ModuleNotFoundError) as exc:
            raise ImportError(
                "The 'langchain-memgraph' integration requires additional dependencies "
                "(langchain-core, memgraph-toolbox, neo4j). "
                "Install them with: pip install langchain-core memgraph-toolbox neo4j"
            ) from exc

    if name == "mcp_memgraph":
        try:
            import importlib

            _mod = importlib.import_module("asi_build.integrations.mcp-memgraph.src.mcp_memgraph")
            globals()["mcp_memgraph"] = _mod
            return _mod
        except (ImportError, ModuleNotFoundError) as exc:
            raise ImportError(
                "The 'mcp-memgraph' integration requires additional dependencies "
                "(mcp, memgraph-toolbox). "
                "Install them with: pip install mcp memgraph-toolbox"
            ) from exc

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
