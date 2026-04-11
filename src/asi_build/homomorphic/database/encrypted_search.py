"""Searchable encryption for databases."""

import hashlib
from typing import Dict, List, Set

from ..schemes.ckks import CKKSScheme


class SearchableEncryption:
    """Searchable encryption scheme for encrypted databases."""

    def __init__(self, scheme: CKKSScheme):
        self.scheme = scheme
        self.encrypted_index = {}
        self.document_store = {}

    def add_document(self, doc_id: str, content: str):
        """Add document with searchable encryption."""
        # Extract keywords
        keywords = self._extract_keywords(content)

        # Store document
        self.document_store[doc_id] = content

        # Add to searchable index
        for keyword in keywords:
            encrypted_keyword = self._encrypt_keyword(keyword)
            if encrypted_keyword not in self.encrypted_index:
                self.encrypted_index[encrypted_keyword] = set()
            self.encrypted_index[encrypted_keyword].add(doc_id)

    def search(self, query: str) -> List[str]:
        """Search for documents containing query."""
        encrypted_query = self._encrypt_keyword(query)

        if encrypted_query in self.encrypted_index:
            return list(self.encrypted_index[encrypted_query])

        return []

    def _extract_keywords(self, content: str) -> Set[str]:
        """Extract keywords from content."""
        # Simple word extraction
        words = content.lower().split()
        return set(word.strip('.,!?";') for word in words if len(word) > 2)

    def _encrypt_keyword(self, keyword: str) -> str:
        """Encrypt keyword for indexing."""
        # Simple hash-based encryption for demo
        return hashlib.sha256(keyword.encode()).hexdigest()


class EncryptedSearch:
    """High-level encrypted search interface."""

    def __init__(self, scheme: CKKSScheme):
        self.scheme = scheme
        self.se = SearchableEncryption(scheme)

    def index_data(self, data: Dict[str, str]):
        """Index data for searching."""
        for doc_id, content in data.items():
            self.se.add_document(doc_id, content)

    def search_encrypted(self, query: str) -> List[str]:
        """Perform encrypted search."""
        return self.se.search(query)
