"""
Database analysis and abstraction layer.

This package provides database-agnostic interfaces and implementations
for analyzing SQL database structures.
"""

try:
    from .interface import (
        ColumnInfo,
        DatabaseAnalyzer,
        DatabaseStructure,
        ForeignKeyInfo,
        RelationshipInfo,
        TableInfo,
        TableType,
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    DatabaseAnalyzer = None
    ColumnInfo = None
    ForeignKeyInfo = None
    TableInfo = None
    TableType = None
    RelationshipInfo = None
    DatabaseStructure = None
try:
    from .factory import DatabaseAnalyzerFactory
except (ImportError, ModuleNotFoundError, SyntaxError):
    DatabaseAnalyzerFactory = None
try:
    from .data_interface import DatabaseDataInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    DatabaseDataInterface = None

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
