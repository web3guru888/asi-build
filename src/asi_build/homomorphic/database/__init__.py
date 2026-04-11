"""Encrypted database operations."""

try:
    from .encrypted_db import EncryptedDatabase, EncryptedQuery
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedDatabase = None
    EncryptedQuery = None
try:
    from .encrypted_indexing import EncryptedIndex, BloomFilterIndex
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedIndex = None
    BloomFilterIndex = None
try:
    from .encrypted_search import EncryptedSearch, SearchableEncryption
except (ImportError, ModuleNotFoundError, SyntaxError):
    EncryptedSearch = None
    SearchableEncryption = None

__all__ = ["EncryptedDatabase", "EncryptedQuery", "EncryptedIndex", "BloomFilterIndex", "EncryptedSearch", "SearchableEncryption"]