"""
Data Manager for IPFS-based Audit Trail Storage

Provides high-level data management functionality for storing and retrieving
audit trail data with encryption, compression, and metadata management.
"""

import json
import gzip
import hashlib
import asyncio
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import base64
import logging

from .ipfs_client import IPFSClient, IPFSError

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """Represents an audit record for storage in IPFS"""
    id: str
    event_type: str
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    hash: Optional[str] = None
    signature: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditRecord':
        """Create from dictionary"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class StorageResult:
    """Result of storing data in IPFS"""
    ipfs_hash: str
    size: int
    compressed_size: Optional[int] = None
    encrypted: bool = False
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DataManager:
    """
    High-level data manager for audit trail storage in IPFS
    
    Provides functionality for:
    - JSON data serialization/deserialization
    - Compression for large datasets
    - Batch operations
    - Data integrity verification
    """
    
    def __init__(
        self,
        ipfs_client: IPFSClient,
        compress_threshold: int = 1024,  # Compress data larger than 1KB
        enable_compression: bool = True
    ):
        """
        Initialize data manager
        
        Args:
            ipfs_client: IPFS client instance
            compress_threshold: Size threshold for compression (bytes)
            enable_compression: Whether to enable compression
        """
        self.ipfs_client = ipfs_client
        self.compress_threshold = compress_threshold
        self.enable_compression = enable_compression
        
    async def store_audit_record(self, record: AuditRecord) -> StorageResult:
        """
        Store a single audit record
        
        Args:
            record: Audit record to store
            
        Returns:
            Storage result with IPFS hash and metadata
        """
        try:
            # Calculate hash for integrity
            record_data = record.to_dict()
            record_json = json.dumps(record_data, sort_keys=True, default=str)
            record.hash = hashlib.sha256(record_json.encode()).hexdigest()
            
            # Store in IPFS
            ipfs_hash = await self._store_json_data(record_data)
            
            result = StorageResult(
                ipfs_hash=ipfs_hash,
                size=len(record_json),
                encrypted=False
            )
            
            logger.info(f"Stored audit record {record.id} with hash {ipfs_hash}")
            return result
            
        except Exception as e:
            raise IPFSError(f"Failed to store audit record: {str(e)}")
            
    async def retrieve_audit_record(self, ipfs_hash: str) -> AuditRecord:
        """
        Retrieve an audit record from IPFS
        
        Args:
            ipfs_hash: IPFS hash of the record
            
        Returns:
            Retrieved audit record
        """
        try:
            data = await self._retrieve_json_data(ipfs_hash)
            record = AuditRecord.from_dict(data)
            
            # Verify hash integrity if available
            if record.hash:
                record_copy = AuditRecord.from_dict(data)
                record_copy.hash = None
                calculated_hash = hashlib.sha256(
                    json.dumps(record_copy.to_dict(), sort_keys=True, default=str).encode()
                ).hexdigest()
                
                if calculated_hash != record.hash:
                    logger.warning(f"Hash mismatch for record {record.id}")
                    
            logger.info(f"Retrieved audit record {record.id}")
            return record
            
        except Exception as e:
            raise IPFSError(f"Failed to retrieve audit record: {str(e)}")
            
    async def store_batch_records(self, records: List[AuditRecord]) -> List[StorageResult]:
        """
        Store multiple audit records in batch
        
        Args:
            records: List of audit records to store
            
        Returns:
            List of storage results
        """
        try:
            tasks = [self.store_audit_record(record) for record in records]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to store record {records[i].id}: {str(result)}")
                else:
                    successful_results.append(result)
                    
            logger.info(f"Batch stored {len(successful_results)}/{len(records)} records")
            return successful_results
            
        except Exception as e:
            raise IPFSError(f"Failed to batch store records: {str(e)}")
            
    async def store_audit_collection(
        self,
        collection_name: str,
        records: List[AuditRecord],
        metadata: Optional[Dict[str, Any]] = None
    ) -> StorageResult:
        """
        Store a collection of audit records as a single IPFS object
        
        Args:
            collection_name: Name for the collection
            records: List of audit records
            metadata: Optional metadata for the collection
            
        Returns:
            Storage result for the collection
        """
        try:
            collection_data = {
                'name': collection_name,
                'created_at': datetime.now().isoformat(),
                'record_count': len(records),
                'records': [record.to_dict() for record in records],
                'metadata': metadata or {}
            }
            
            # Calculate collection hash
            collection_json = json.dumps(collection_data, sort_keys=True, default=str)
            collection_hash = hashlib.sha256(collection_json.encode()).hexdigest()
            collection_data['collection_hash'] = collection_hash
            
            ipfs_hash = await self._store_json_data(collection_data)
            
            result = StorageResult(
                ipfs_hash=ipfs_hash,
                size=len(collection_json),
                encrypted=False
            )
            
            logger.info(f"Stored collection '{collection_name}' with {len(records)} records")
            return result
            
        except Exception as e:
            raise IPFSError(f"Failed to store audit collection: {str(e)}")
            
    async def retrieve_audit_collection(self, ipfs_hash: str) -> Tuple[str, List[AuditRecord], Dict]:
        """
        Retrieve an audit collection from IPFS
        
        Args:
            ipfs_hash: IPFS hash of the collection
            
        Returns:
            Tuple of (collection_name, records_list, metadata)
        """
        try:
            data = await self._retrieve_json_data(ipfs_hash)
            
            collection_name = data['name']
            metadata = data.get('metadata', {})
            
            records = [
                AuditRecord.from_dict(record_data)
                for record_data in data['records']
            ]
            
            # Verify collection hash if available
            if 'collection_hash' in data:
                data_copy = data.copy()
                del data_copy['collection_hash']
                calculated_hash = hashlib.sha256(
                    json.dumps(data_copy, sort_keys=True, default=str).encode()
                ).hexdigest()
                
                if calculated_hash != data['collection_hash']:
                    logger.warning(f"Collection hash mismatch for '{collection_name}'")
                    
            logger.info(f"Retrieved collection '{collection_name}' with {len(records)} records")
            return collection_name, records, metadata
            
        except Exception as e:
            raise IPFSError(f"Failed to retrieve audit collection: {str(e)}")
            
    async def _store_json_data(self, data: Dict[str, Any]) -> str:
        """Store JSON data in IPFS with optional compression"""
        json_str = json.dumps(data, indent=2, default=str)
        json_bytes = json_str.encode('utf-8')
        
        # Apply compression if enabled and data is large enough
        if self.enable_compression and len(json_bytes) > self.compress_threshold:
            compressed_data = gzip.compress(json_bytes)
            
            # Only use compression if it reduces size significantly
            if len(compressed_data) < len(json_bytes) * 0.9:
                storage_data = {
                    'compressed': True,
                    'original_size': len(json_bytes),
                    'data': base64.b64encode(compressed_data).decode('ascii')
                }
                return await self.ipfs_client.add_json(storage_data)
                
        # Store uncompressed
        return await self.ipfs_client.add_json(data)
        
    async def _retrieve_json_data(self, ipfs_hash: str) -> Dict[str, Any]:
        """Retrieve JSON data from IPFS with decompression support"""
        data = await self.ipfs_client.get_json(ipfs_hash)
        
        # Check if data is compressed
        if isinstance(data, dict) and data.get('compressed'):
            compressed_bytes = base64.b64decode(data['data'].encode('ascii'))
            json_bytes = gzip.decompress(compressed_bytes)
            return json.loads(json_bytes.decode('utf-8'))
            
        return data
        
    async def get_data_stats(self, ipfs_hash: str) -> Dict[str, Any]:
        """
        Get statistics about stored data
        
        Args:
            ipfs_hash: IPFS hash of the data
            
        Returns:
            Dictionary with data statistics
        """
        try:
            # This would require IPFS API to get object stats
            # For now, return basic info
            data = await self._retrieve_json_data(ipfs_hash)
            
            stats = {
                'ipfs_hash': ipfs_hash,
                'type': 'unknown',
                'size_estimate': len(json.dumps(data, default=str))
            }
            
            # Detect data type
            if 'records' in data and 'name' in data:
                stats['type'] = 'audit_collection'
                stats['record_count'] = len(data['records'])
            elif 'event_type' in data and 'timestamp' in data:
                stats['type'] = 'audit_record'
                
            return stats
            
        except Exception as e:
            raise IPFSError(f"Failed to get data stats: {str(e)}")


class EncryptedDataManager(DataManager):
    """
    Encrypted version of DataManager with additional security features
    
    Provides:
    - AES encryption for sensitive data
    - RSA key management
    - Digital signatures
    """
    
    def __init__(
        self,
        ipfs_client: IPFSClient,
        encryption_key: Optional[bytes] = None,
        private_key: Optional[rsa.RSAPrivateKey] = None,
        public_key: Optional[rsa.RSAPublicKey] = None,
        **kwargs
    ):
        """
        Initialize encrypted data manager
        
        Args:
            ipfs_client: IPFS client instance
            encryption_key: AES encryption key (will generate if None)
            private_key: RSA private key for signing
            public_key: RSA public key for verification
            **kwargs: Additional arguments for DataManager
        """
        super().__init__(ipfs_client, **kwargs)
        
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)
        
        if private_key is None:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()
        else:
            self.private_key = private_key
            self.public_key = public_key or private_key.public_key()
            
    def generate_key_pair(self) -> Tuple[bytes, bytes]:
        """Generate and return PEM-encoded key pair"""
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
        
    def sign_data(self, data: bytes) -> bytes:
        """Sign data with private key"""
        signature = self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature
        
    def verify_signature(self, data: bytes, signature: bytes, public_key: Optional[rsa.RSAPublicKey] = None) -> bool:
        """Verify signature with public key"""
        key = public_key or self.public_key
        try:
            key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
            
    async def store_audit_record(self, record: AuditRecord, encrypt: bool = True) -> StorageResult:
        """Store audit record with optional encryption and signing"""
        try:
            record_data = record.to_dict()
            record_json = json.dumps(record_data, sort_keys=True, default=str)
            
            # Sign the data
            signature = self.sign_data(record_json.encode())
            record.signature = base64.b64encode(signature).decode('ascii')
            
            # Update record with signature
            record_data = record.to_dict()
            
            if encrypt:
                # Encrypt the data
                encrypted_data = self.fernet.encrypt(
                    json.dumps(record_data, default=str).encode()
                )
                
                storage_data = {
                    'encrypted': True,
                    'data': base64.b64encode(encrypted_data).decode('ascii'),
                    'public_key': base64.b64encode(
                        self.public_key.public_bytes(
                            encoding=serialization.Encoding.DER,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                    ).decode('ascii')
                }
                
                ipfs_hash = await self.ipfs_client.add_json(storage_data)
                
                result = StorageResult(
                    ipfs_hash=ipfs_hash,
                    size=len(record_json),
                    encrypted=True
                )
            else:
                ipfs_hash = await self._store_json_data(record_data)
                result = StorageResult(
                    ipfs_hash=ipfs_hash,
                    size=len(record_json),
                    encrypted=False
                )
                
            logger.info(f"Stored encrypted audit record {record.id}")
            return result
            
        except Exception as e:
            raise IPFSError(f"Failed to store encrypted audit record: {str(e)}")
            
    async def retrieve_audit_record(self, ipfs_hash: str) -> AuditRecord:
        """Retrieve and decrypt audit record"""
        try:
            data = await self.ipfs_client.get_json(ipfs_hash)
            
            if isinstance(data, dict) and data.get('encrypted'):
                # Decrypt the data
                encrypted_bytes = base64.b64decode(data['data'].encode('ascii'))
                decrypted_data = self.fernet.decrypt(encrypted_bytes)
                record_data = json.loads(decrypted_data.decode('utf-8'))
            else:
                record_data = data
                
            record = AuditRecord.from_dict(record_data)
            
            # Verify signature if present
            if record.signature:
                # Remove signature for verification
                record_copy = AuditRecord.from_dict(record_data)
                record_copy.signature = None
                verification_data = json.dumps(
                    record_copy.to_dict(), 
                    sort_keys=True, 
                    default=str
                ).encode()
                
                signature_bytes = base64.b64decode(record.signature.encode('ascii'))
                
                if not self.verify_signature(verification_data, signature_bytes):
                    logger.warning(f"Signature verification failed for record {record.id}")
                    
            logger.info(f"Retrieved and verified audit record {record.id}")
            return record
            
        except Exception as e:
            raise IPFSError(f"Failed to retrieve encrypted audit record: {str(e)}")