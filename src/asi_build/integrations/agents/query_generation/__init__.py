"""
Query generation and schema utilities.

This package provides utilities for generating Cypher queries
and handling schema transformations.
"""

try:
    from .cypher_generator import CypherGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    CypherGenerator = None
try:
    from .schema_utilities import SchemaUtilities
except (ImportError, ModuleNotFoundError, SyntaxError):
    SchemaUtilities = None

__all__ = [
    "CypherGenerator",
    "SchemaUtilities",
]
