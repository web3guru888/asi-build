"""
Core business logic for SQL to Memgraph migration.

This package contains the main migration orchestration and graph modeling logic.
"""

try:
    from .migration_agent import SQLToMemgraphAgent
except (ImportError, ModuleNotFoundError, SyntaxError):
    SQLToMemgraphAgent = None
try:
    from .graph_modeling import GraphModel, GraphNode, GraphRelationship, HyGM
except (ImportError, ModuleNotFoundError, SyntaxError):
    HyGM = None
    GraphModel = None
    GraphNode = None
    GraphRelationship = None

__all__ = [
    "SQLToMemgraphAgent",
    "HyGM",
    "GraphModel",
    "GraphNode",
    "GraphRelationship",
]
