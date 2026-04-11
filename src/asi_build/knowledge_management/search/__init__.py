"""
Search Module - Intelligent Information Retrieval
================================================

Advanced search capabilities for the omniscience network.
"""

try:
    from .intelligent_search import IntelligentSearch, SearchQuery, SearchResponse, SearchResult
except (ImportError, ModuleNotFoundError, SyntaxError):
    IntelligentSearch = None
    SearchQuery = None
    SearchResult = None
    SearchResponse = None

__all__ = ["IntelligentSearch", "SearchQuery", "SearchResult", "SearchResponse"]
