"""
Web3 Integration Module for Kenny AGI Blockchain Audit Trail

This module provides Web3 integration for Ethereum and Polygon networks,
enabling smart contract deployment and interaction for audit trail functionality.
"""

try:
    from .web3_client import Web3Client, Web3Error
except (ImportError, ModuleNotFoundError, SyntaxError):
    Web3Client = None
    Web3Error = None
try:
    from .contract_manager import ContractInterface, ContractManager
except (ImportError, ModuleNotFoundError, SyntaxError):
    ContractManager = None
    ContractInterface = None
try:
    from .transaction_manager import TransactionManager, TransactionStatus
except (ImportError, ModuleNotFoundError, SyntaxError):
    TransactionManager = None
    TransactionStatus = None
try:
    from .network_config import (
        ETHEREUM_GOERLI,
        ETHEREUM_MAINNET,
        POLYGON_MAINNET,
        POLYGON_MUMBAI,
        NetworkConfig,
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    NetworkConfig = None
    ETHEREUM_MAINNET = None
    ETHEREUM_GOERLI = None
    POLYGON_MAINNET = None
    POLYGON_MUMBAI = None
try:
    from .gas_optimizer import GasOptimizer
except (ImportError, ModuleNotFoundError, SyntaxError):
    GasOptimizer = None
try:
    from .event_listener import ContractEventFilter, EventListener
except (ImportError, ModuleNotFoundError, SyntaxError):
    EventListener = None
    ContractEventFilter = None

__all__ = [
    "Web3Client",
    "Web3Error",
    "ContractManager",
    "ContractInterface",
    "TransactionManager",
    "TransactionStatus",
    "NetworkConfig",
    "ETHEREUM_MAINNET",
    "ETHEREUM_GOERLI",
    "POLYGON_MAINNET",
    "POLYGON_MUMBAI",
    "GasOptimizer",
    "EventListener",
    "ContractEventFilter",
]
