"""
Kenny Graph Intelligence System

A comprehensive graph-based intelligence system that enables Kenny to think 
"community by community" for faster and more accurate automation decisions.

This package implements:
- Memgraph database integration
- Knowledge graph schema and management
- Community detection algorithms
- FastToG reasoning engine
- Graph-based workflow orchestration
"""

from .schema import (
    NodeType, RelationshipType, KnowledgeGraphSchema,
    UIElementNode, WorkflowNode, CommunityNode, ApplicationNode,
    ScreenNode, PatternNode, ErrorNode, Relationship,
    create_ui_element, create_community, create_workflow
)
from .memgraph_connection import MemgraphConnection, create_memgraph_connection
from .schema_manager import SchemaManager

__version__ = "1.0.0"
__author__ = "Kenny AI Team"

__all__ = [
    # Core schema
    'NodeType', 'RelationshipType', 'KnowledgeGraphSchema',
    
    # Node types
    'UIElementNode', 'WorkflowNode', 'CommunityNode', 'ApplicationNode',
    'ScreenNode', 'PatternNode', 'ErrorNode', 'Relationship',
    
    # Factory functions
    'create_ui_element', 'create_community', 'create_workflow',
    
    # Database connections
    'MemgraphConnection', 'create_memgraph_connection',
    
    # Management
    'SchemaManager'
]