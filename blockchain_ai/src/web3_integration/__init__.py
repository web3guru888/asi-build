"""
Web3 Integration Module for Kenny AGI Blockchain Audit Trail

This module provides Web3 integration for Ethereum and Polygon networks,
enabling smart contract deployment and interaction for audit trail functionality.
"""

from .web3_client import Web3Client, Web3Error
from .contract_manager import ContractManager, ContractInterface
from .transaction_manager import TransactionManager, TransactionStatus
from .network_config import NetworkConfig, ETHEREUM_MAINNET, ETHEREUM_GOERLI, POLYGON_MAINNET, POLYGON_MUMBAI
from .gas_optimizer import GasOptimizer
from .event_listener import EventListener, ContractEventFilter

__all__ = [
    'Web3Client',
    'Web3Error',
    'ContractManager', 
    'ContractInterface',
    'TransactionManager',
    'TransactionStatus',
    'NetworkConfig',
    'ETHEREUM_MAINNET',
    'ETHEREUM_GOERLI', 
    'POLYGON_MAINNET',
    'POLYGON_MUMBAI',
    'GasOptimizer',
    'EventListener',
    'ContractEventFilter'
]