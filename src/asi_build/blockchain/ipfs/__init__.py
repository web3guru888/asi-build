"""
IPFS Integration Module for Kenny AGI Blockchain Audit Trail

This module provides functionality for storing and retrieving audit data
from the InterPlanetary File System (IPFS) for decentralized storage.
"""

try:
    from .ipfs_client import IPFSClient, IPFSError
except (ImportError, ModuleNotFoundError, SyntaxError):
    IPFSClient = None
    IPFSError = None
try:
    from .data_manager import DataManager, EncryptedDataManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    DataManager = None
    EncryptedDataManager = None
try:
    from .pinning_service import PinningService, PinataService, InfuraService
except (ImportError, ModuleNotFoundError, SyntaxError):
    PinningService = None
    PinataService = None
    InfuraService = None

__all__ = [
    'IPFSClient',
    'IPFSError', 
    'DataManager',
    'EncryptedDataManager',
    'PinningService',
    'PinataService',
    'InfuraService'
]