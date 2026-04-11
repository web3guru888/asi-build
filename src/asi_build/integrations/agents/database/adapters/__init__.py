"""
Database adapter implementations for different database systems.
"""

try:
    from .mysql import MySQLAnalyzer
except (ImportError, ModuleNotFoundError, SyntaxError):
    MySQLAnalyzer = None

__all__ = [
    "MySQLAnalyzer",
]
