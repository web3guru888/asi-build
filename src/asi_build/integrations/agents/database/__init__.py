"""
Database analysis and abstraction layer.

This package provides database-agnostic interfaces and implementations
for analyzing SQL database structures.
"""

from .interface import (
    DatabaseAnalyzer,
    ColumnInfo,
    ForeignKeyInfo,
    TableInfo,
    TableType,
    RelationshipInfo,
    DatabaseStructure,
)
from .factory import DatabaseAnalyzerFactory
from .data_interface import DatabaseDataInterface

__all__ = [
    "DatabaseAnalyzer",
    "ColumnInfo",
    "ForeignKeyInfo",
    "TableInfo",
    "TableType",
    "RelationshipInfo",
    "DatabaseStructure",
    "DatabaseAnalyzerFactory",
    "DatabaseDataInterface",
]
