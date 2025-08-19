"""Encrypted database implementation with homomorphic operations."""

import json
from typing import Dict, List, Any, Optional
from ..schemes.ckks import CKKSScheme, CKKSCiphertext

class EncryptedDatabase:
    """Database that stores and operates on encrypted data."""
    
    def __init__(self, scheme: CKKSScheme):
        self.scheme = scheme
        self.tables: Dict[str, Dict[str, CKKSCiphertext]] = {}
        self.metadata: Dict[str, Dict] = {}
    
    def create_table(self, table_name: str, schema: Dict[str, str]):
        """Create an encrypted table."""
        self.tables[table_name] = {}
        self.metadata[table_name] = {"schema": schema, "row_count": 0}
    
    def insert_row(self, table_name: str, row_data: Dict[str, Any]) -> str:
        """Insert encrypted row into table."""
        if table_name not in self.tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        row_id = f"row_{self.metadata[table_name]['row_count']}"
        
        # Encrypt each field
        encrypted_row = {}
        for field, value in row_data.items():
            if isinstance(value, (int, float)):
                plaintext = self.scheme.encode([complex(value)])
                encrypted_row[field] = self.scheme.encrypt(plaintext)
            else:
                # For strings, hash to number first
                hash_val = hash(str(value)) % (2**20)
                plaintext = self.scheme.encode([complex(hash_val)])
                encrypted_row[field] = self.scheme.encrypt(plaintext)
        
        self.tables[table_name][row_id] = encrypted_row
        self.metadata[table_name]["row_count"] += 1
        
        return row_id
    
    def encrypted_sum(self, table_name: str, column: str) -> CKKSCiphertext:
        """Compute encrypted sum of a column."""
        if table_name not in self.tables:
            raise ValueError(f"Table {table_name} does not exist")
        
        table = self.tables[table_name]
        if not table:
            # Return zero
            zero_plaintext = self.scheme.encode([0])
            return self.scheme.encrypt(zero_plaintext)
        
        # Sum all values in column
        result = None
        for row_id, row_data in table.items():
            if column in row_data:
                if result is None:
                    result = row_data[column]
                else:
                    result = self.scheme.add(result, row_data[column])
        
        return result
    
    def encrypted_count(self, table_name: str) -> int:
        """Get count of rows (not encrypted since it's metadata)."""
        return self.metadata[table_name]["row_count"]

class EncryptedQuery:
    """Query processor for encrypted databases."""
    
    def __init__(self, database: EncryptedDatabase):
        self.database = database
    
    def select_sum(self, table_name: str, column: str) -> CKKSCiphertext:
        """SELECT SUM(column) FROM table."""
        return self.database.encrypted_sum(table_name, column)
    
    def select_count(self, table_name: str) -> int:
        """SELECT COUNT(*) FROM table."""
        return self.database.encrypted_count(table_name)